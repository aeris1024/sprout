import json
import re
import shutil
from pathlib import Path
from urllib.parse import unquote

import pytest
import zstandard
from PIL import Image
from typer.testing import CliRunner

from sprout import repository as repository_module
from sprout.archive import INCOMPLETE_MARKER, INCOMPLETE_SUFFIX
from sprout import cli
from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository

runner = CliRunner()
DIRECTORY_NAME = re.compile(r"^\d{8}T\d{6}\.\d{6}Z_[0-9a-f]{12}$")
LINK = re.compile(r'(?:href|src)="([^"]*)"')


def write(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    repo = Repository.init(tmp_path / "project")
    monkeypatch.chdir(repo.root)
    asset = write(repo.root / "art" / "日本語 file.bin", b"v1")
    readme = write(repo.root / "readme.txt", b"same content")
    repo.track([asset, readme])
    first = repo.commit("first").commit_id
    asset.write_bytes(b"main-v2")
    main_tip = repo.commit("main work").commit_id

    repo.create_branch("side", start_point=first, switch=True)
    asset.write_bytes(b"side-v2")
    extra = write(repo.root / "deep" / "nested" / "extra.dat", b"side only")
    repo.track([extra])
    side_tip = repo.commit("side work").commit_id
    image = tmp_path / "in" / "thumb.png"
    image.parent.mkdir()
    Image.new("RGB", (4, 4), "green").save(image)
    repo.set_thumbnail(side_tip, image)
    sources = [
        write(tmp_path / "a" / "clip.wav", b"RIFF-first"),
        write(tmp_path / "b" / "clip.wav", b"RIFF-second"),
        write(tmp_path / "c" / "model.stl", b"solid cube"),
    ]
    previews = repo.add_previews(side_tip, sources)
    order = [previews[2].id, previews[0].id, previews[1].id]
    repo.reorder_previews(side_tip, order)
    repo.set_note(side_tip, "review <this> branch")
    repo.add_label(side_tip, "Candidate")
    repo.switch("main")
    repo.create_tag("baseline", first, "shared root")
    repo.delete_branch("side")
    return {
        "repo": repo,
        "first": first,
        "main_tip": main_tip,
        "side_tip": side_tip,
        "preview_order": order,
        "preview_content": {item.id: source.read_bytes() for item, source in zip(previews, sources)},
    }


def main_json_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, args: list[str]) -> dict:
    monkeypatch.setattr(cli.sys, "argv", ["sprout", *args])
    assert cli.main() == 1
    return json.loads(capsys.readouterr().err)


def broken_links(root: Path) -> list[str]:
    broken = []
    for page in root.rglob("*.html"):
        for link in LINK.findall(page.read_text(encoding="utf-8")):
            target = unquote(link.split("#", 1)[0])
            if target and not (page.parent / target).exists():
                broken.append(f"{page.relative_to(root)} -> {link}")
    return broken


def test_archive_expands_every_commit_with_metadata_html_and_attachments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = history(tmp_path, monkeypatch)
    repo: Repository = data["repo"]
    output = tmp_path / "out" / "archive"

    plan = repo.archive(output)

    model = json.loads((output / "archive.json").read_text(encoding="utf-8"))
    commits = {commit["id"]: commit for commit in model["commits"]}
    # The side commit is unreachable from every live branch but still archived.
    assert set(commits) == {data["first"], data["main_tip"], data["side_tip"]}
    assert plan.commits == 3
    assert [commit["id"] for commit in model["commits"]] == [data["side_tip"], data["main_tip"], data["first"]]
    with repo.connect() as db:
        meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
    assert model["format"] == "sprout-static-archive"
    assert model["repository"]["repository_id"] == meta["repository_id"]
    assert model["repository"]["repository_created_at"] == meta["repository_created_at"]
    assert "repository_id" in (output / "README.txt").read_text(encoding="utf-8")
    side_branch = next(branch for branch in model["branches"] if branch["name"] == "side")
    assert side_branch["deleted"] is True
    assert model["tags"] == [
        {"name": "baseline", "commit_id": data["first"], "comment": "shared root",
         "created_at": model["tags"][0]["created_at"]}
    ]

    # Directory names carry the UTC time and short ID and reproduce the commit files.
    directories = sorted(path.name for path in (output / "snapshots").iterdir())
    assert len(directories) == 3 and all(DIRECTORY_NAME.match(name) for name in directories)
    for commit in model["commits"]:
        assert commit["directory"].endswith(commit["id"][:12])
        assert json.loads((output / commit["directory"] / "commit.json").read_text(encoding="utf-8")) == commit
        assert {item["path"] for item in commit["files"]} == set(repo.manifest(commit["id"]))
        for item in commit["files"]:
            content = (output / commit["directory"] / "files" / item["path"]).read_bytes()
            assert len(content) == item["size"]
            assert repository_module.hashlib.sha256(content).hexdigest() == item["sha256"]
    side = commits[data["side_tip"]]
    assert (output / side["directory"] / "files" / "deep" / "nested" / "extra.dat").read_bytes() == b"side only"
    assert (output / side["directory"] / "files" / "art" / "日本語 file.bin").read_bytes() == b"side-v2"
    assert commits[data["main_tip"]]["parent_id"] == data["first"]
    assert side["parent_id"] == data["first"]
    assert commits[data["first"]]["children_ids"] == [data["main_tip"], data["side_tip"]]
    assert side["note"] == "review <this> branch"
    assert side["labels"] == ["Candidate"]
    assert side["branch_name"] == "side"

    # Previews keep their order, ID, name and media type; equal names do not collide.
    assert [preview["id"] for preview in side["previews"]] == data["preview_order"]
    assert [preview["position"] for preview in side["previews"]] == [0, 1, 2]
    assert [preview["original_name"] for preview in side["previews"]] == ["model.stl", "clip.wav", "clip.wav"]
    assert side["previews"][1]["media_type"].startswith("audio/")
    for preview in side["previews"]:
        stored = output / preview["archive_path"]
        assert stored.name == preview["original_name"]
        assert preview["id"] in preview["archive_path"]
        assert stored.read_bytes() == data["preview_content"][preview["id"]]
        assert preview["sha256"] == repository_module.hashlib.sha256(stored.read_bytes()).hexdigest()
    assert len({preview["archive_path"] for preview in side["previews"]}) == 3
    thumbnail = side["thumbnail"]
    assert thumbnail["original_name"] == "thumb.png" and thumbnail["media_type"] == "image/png"
    assert (output / thumbnail["archive_path"]).is_file()

    # HTML shows everything through relative links, in stored preview order, offline.
    index = (output / "index.html").read_text(encoding="utf-8")
    for commit in model["commits"]:
        assert commit["id"] in index
        assert commit["created_at"] in index
        assert f'href="{commit["directory"]}/index.html"' in index
    for text in ["first", "main work", "side work", "baseline", "Candidate", "review &lt;this&gt; branch", "削除済み"]:
        assert text in index
    page = (output / side["directory"] / "index.html").read_text(encoding="utf-8")
    positions = [page.index(f'id="a-{attachment_id}"') for attachment_id in data["preview_order"]]
    assert positions == sorted(positions)
    assert "<audio controls" in page and '<img src="attachments/thumbnail/' in page
    assert "files/deep/nested/extra.dat" in page
    assert data["first"][:12] in page and "Candidate" in page
    for html_page in output.rglob("*.html"):
        text = html_page.read_text(encoding="utf-8").lower()
        assert "<script" not in text and "http://" not in text and "https://" not in text
        assert "<link" not in text
    assert broken_links(output) == []

    copied = tmp_path / "elsewhere" / "copy"
    shutil.copytree(output, copied)
    assert broken_links(copied) == []
    assert plan.files == sum(1 for path in output.rglob("*") if path.is_file())
    assert not (output / INCOMPLETE_MARKER).exists()
    assert not output.with_name(f".archive{INCOMPLETE_SUFFIX}").exists()


def test_archive_dry_run_reports_counts_and_space_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = history(tmp_path, monkeypatch)
    output = tmp_path / "planned"

    result = runner.invoke(app, ["archive", "--output", str(output), "--dry-run", "--json"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["dry_run"] is True
    assert report["commits"] == 3
    assert report["sufficient_space"] is True
    assert report["free_bytes"] > 0
    assert not output.exists()
    plan = data["repo"].archive(output)
    assert report["files"] == plan.files
    written = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    assert abs(report["estimated_bytes"] - written) < 200  # only generated_at may differ

    text = runner.invoke(app, ["archive", "-o", str(tmp_path / "other"), "--dry-run"])
    assert text.exit_code == 0, text.output
    assert "Commits:         3" in text.stdout and "Free space:" in text.stdout


def test_archive_reports_insufficient_space_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    data = history(tmp_path, monkeypatch)
    output = tmp_path / "full"
    monkeypatch.setattr(
        repository_module.shutil, "disk_usage", lambda _path: shutil._ntuple_diskusage(10, 9, 1)
    )

    with pytest.raises(SproutError) as error:
        data["repo"].archive(output)

    assert error.value.code == "archive_insufficient_space"
    assert error.value.details["free_bytes"] == 1
    assert not output.exists()
    assert not output.with_name(f".full{INCOMPLETE_SUFFIX}").exists()
    dry_run = runner.invoke(app, ["archive", "-o", str(output), "--dry-run"])
    assert dry_run.exit_code == 1
    assert "Not enough free space" in dry_run.stdout
    failure = main_json_error(monkeypatch, capsys, ["archive", "-o", str(output), "--json"])
    assert failure["code"] == "archive_insufficient_space"


def test_archive_refuses_non_empty_output_and_accepts_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = history(tmp_path, monkeypatch)
    repo: Repository = data["repo"]
    occupied = tmp_path / "occupied"
    keep = write(occupied / "keep.txt", b"mine")

    with pytest.raises(SproutError) as error:
        repo.archive(occupied)
    assert error.value.code == "archive_output_not_empty"
    assert [path.name for path in occupied.iterdir()] == ["keep.txt"]
    assert keep.read_bytes() == b"mine"
    with pytest.raises(SproutError, match="not a directory"):
        repo.archive(keep)
    with pytest.raises(SproutError, match="Sprout metadata"):
        repo.archive(repo.control / "archive")

    empty = tmp_path / "empty"
    empty.mkdir()
    repo.archive(empty)
    assert (empty / "archive.json").is_file()
    with pytest.raises(SproutError, match="not empty"):
        repo.archive(empty)


def test_archive_replaces_only_marked_incomplete_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = history(tmp_path, monkeypatch)
    repo: Repository = data["repo"]
    output = tmp_path / "result"
    staging = tmp_path / f".result{INCOMPLETE_SUFFIX}"
    write(staging / INCOMPLETE_MARKER, b"interrupted")
    write(staging / "snapshots" / "partial.bin", b"partial")

    plan = repo.plan_archive(output)
    assert plan.removes_incomplete is True
    repo.archive(output)
    assert (output / "archive.json").is_file()
    assert not (output / "snapshots" / "partial.bin").exists()
    assert not staging.exists()

    other = tmp_path / "other"
    foreign = write(tmp_path / f".other{INCOMPLETE_SUFFIX}" / "data.txt", b"not ours")
    with pytest.raises(SproutError) as error:
        repo.archive(other)
    assert error.value.code == "archive_staging_conflict"
    assert foreign.read_bytes() == b"not ours"
    assert not other.exists()


def test_archive_failure_leaves_no_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    data = history(tmp_path, monkeypatch)
    repo: Repository = data["repo"]
    output = tmp_path / "broken"
    staging = tmp_path / f".broken{INCOMPLETE_SUFFIX}"
    extra = repo.manifest(data["side_tip"])["deep/nested/extra.dat"]
    repo._object_path(extra.object_hash).unlink()

    with pytest.raises(SproutError) as error:
        repo.archive(output)
    assert error.value.code == "archive_object_invalid"
    assert error.value.details["commit_id"] == data["side_tip"]
    assert error.value.details["path"] == "deep/nested/extra.dat"
    assert data["side_tip"][:12] in str(error.value)
    assert not output.exists() and not staging.exists()

    # A corrupt attachment is reported by its attachment ID.
    write(repo.root / "deep" / "nested" / "extra.dat", b"side only")
    repo._store_object(repo.root / "deep" / "nested" / "extra.dat")
    preview = repo.previews(data["side_tip"])[0]
    repo._object_path(preview.object_hash).write_bytes(zstandard.ZstdCompressor().compress(b"tampered"))
    failure = main_json_error(monkeypatch, capsys, ["archive", "-o", str(output), "--json"])
    assert failure["code"] == "archive_object_invalid"
    assert failure["details"]["attachment_id"] == preview.id
    assert failure["details"]["role"] == "preview"
    assert not output.exists() and not staging.exists()


def test_archive_cli_writes_archive_and_reports_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history(tmp_path, monkeypatch)
    output = tmp_path / "cli-archive"

    result = runner.invoke(app, ["archive", "--output", str(output), "--json"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["dry_run"] is False and report["commits"] == 3
    assert report["output"] == str(output.resolve())
    assert (output / "index.html").is_file()
    text = runner.invoke(app, ["archive", "-o", str(tmp_path / "plain")])
    assert text.exit_code == 0, text.output
    assert "Archived 3 commit(s)" in text.stdout


def test_archive_writes_paths_longer_than_windows_max_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = Repository.init(tmp_path / "project")
    monkeypatch.chdir(repo.root)
    relative = "/".join(["segment-" + "n" * 20] * 4) + "/file.txt"
    source = write(repo.root / Path(relative), b"deep")
    repo.track([source])
    repo.commit("deep")
    output = tmp_path / ("o" * 100) / "archive"

    repo.archive(output)

    model = json.loads(repo._extended_path(output / "archive.json").read_text(encoding="utf-8"))
    stored = output / model["commits"][0]["directory"] / "files" / relative
    assert len(str(stored)) > 260
    assert repo._extended_path(stored).read_bytes() == b"deep"
