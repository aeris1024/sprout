import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository

runner = CliRunner()

TABLES = (
    "commits",
    "commit_files",
    "commit_attachments",
    "commit_notes",
    "commit_labels",
    "branches",
    "tags",
    "buds",
    "bud_files",
    "repository_state",
)


def write(root: Path, relative: str, content: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def write_image(path: Path, color: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 12), color).save(path, format="PNG")
    return path


def database(repo: Repository) -> dict[str, list[tuple[object, ...]]]:
    with repo.connect() as db:
        return {
            table: [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in TABLES
        }


def parents(repo: Repository) -> dict[str, str | None]:
    with repo.connect() as db:
        return {row["id"]: row["parent_id"] for row in db.execute("SELECT id, parent_id FROM commits")}


def three_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Repository, Path, str, str, str]:
    repo = Repository.init(tmp_path / "project")
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    first = repo.commit("first").commit_id
    asset.write_bytes(b"v2")
    second = repo.commit("second").commit_id
    asset.write_bytes(b"v3")
    third = repo.commit("third").commit_id
    return repo, asset, first, second, third


def test_delete_middle_commit_reconnects_children_and_drops_its_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = Repository.init(tmp_path / "project")
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    first = repo.commit("first").commit_id
    asset.write_bytes(b"v2")
    thumbnail = write_image(repo.root / "middle.png", "red")
    middle = repo.commit("middle", thumbnail=thumbnail).commit_id
    repo.set_note(middle, "temporary")
    repo.add_label(middle, "draft")
    asset.write_bytes(b"v3")
    last = repo.commit("last").commit_id
    kept = {commit_id: repo.manifest(commit_id) for commit_id in (first, last)}

    result = repo.delete_commit(middle)

    assert result.commit.id == middle
    assert result.parent_id == first
    assert result.reconnected_children == (last,)
    assert result.moved_branches == ()
    assert result.moved_current is False
    assert parents(repo) == {first: None, last: first}
    with pytest.raises(SproutError):
        repo.resolve_commit(middle)
    with repo.connect() as db:
        for table in ("commit_files", "commit_attachments", "commit_notes", "commit_labels"):
            count = db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE commit_id=?", (middle,)
            ).fetchone()[0]
            assert count == 0, table
    assert {commit_id: repo.manifest(commit_id) for commit_id in (first, last)} == kept
    assert repo.head_commit() == last
    assert repo.doctor().ok


def test_delete_tip_moves_every_branch_and_current_to_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, asset, _first, second, third = three_commits(tmp_path, monkeypatch)
    repo.create_branch("alias", start_point=third)
    repo.create_branch("gone", start_point=third)
    repo.delete_branch("gone")

    result = repo.delete_commit(third)

    assert [(branch.name, branch.current) for branch in result.moved_branches] == [
        ("alias", False),
        ("main", True),
    ]
    assert all(branch.commit_id == second for branch in result.moved_branches)
    assert result.moved_current is True
    assert {name: commit_id for name, commit_id, _ in repo.branches()} == {
        "alias": second,
        "main": second,
    }
    assert repo.head_branch() == "main"
    assert repo.current_commit() == second
    assert asset.read_bytes() == b"v3"
    assert [(entry.state, entry.path) for entry in repo.status()] == [("modified", "asset.bin")]
    assert repo.doctor().ok


def test_delete_root_makes_child_a_root_and_lone_root_leaves_no_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, asset, first, second, third = three_commits(tmp_path, monkeypatch)

    result = repo.delete_commit(first)
    assert result.parent_id is None
    assert result.reconnected_children == (second,)
    assert parents(repo) == {second: None, third: second}
    assert repo.doctor().ok

    repo2 = Repository.init(tmp_path / "single")
    monkeypatch.chdir(repo2.root)
    only_asset = write(repo2.root, "asset.bin", b"only")
    repo2.track([only_asset])
    only = repo2.commit("only").commit_id

    lone = repo2.delete_commit(only)
    assert lone.parent_id is None
    assert lone.moved_current is True
    assert {name: commit_id for name, commit_id, _ in repo2.branches()} == {"main": None}
    assert repo2.current_commit() is None
    assert repo2.head_commit() is None
    assert only_asset.read_bytes() == b"only"
    assert [(entry.state, entry.path) for entry in repo2.status()] == [("added", "asset.bin")]
    assert repo2.doctor().ok


def test_delete_tagged_commit_is_rejected_without_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _asset, _first, second, _third = three_commits(tmp_path, monkeypatch)
    repo.create_tag("keep", second)
    before = database(repo)

    for dry_run in (True, False):
        with pytest.raises(SproutError, match="tagged") as exc:
            repo.delete_commit(second, dry_run=dry_run)
        assert exc.value.code == "tagged_commit"
        assert exc.value.details == {"commit_id": second, "tags": ["keep"]}
    assert database(repo) == before


def test_delete_bud_base_rebases_bud_onto_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, asset, _first, second, third = three_commits(tmp_path, monkeypatch)
    repo.restore(second)
    asset.write_bytes(b"draft")
    bud = repo.save_bud()
    repo.restore(third, discard=True)
    repo.restore(second)

    result = repo.delete_commit(third)

    assert result.rebased_buds == ()
    result = repo.delete_commit(second)
    assert result.rebased_buds == (bud.id,)
    rebased = next(item for item in repo.buds() if item.id == bud.id)
    assert rebased.base_commit_id == result.parent_id
    assert rebased.files == bud.files
    assert repo.doctor().ok

    repo.restore(result.parent_id, discard=True)
    restored, stashed = repo.restore_bud(bud.id)
    assert restored.id == bud.id
    assert stashed is None
    assert asset.read_bytes() == b"draft"
    assert repo.current_commit() == result.parent_id


def test_delete_dry_run_reports_the_same_effects_without_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, asset, _first, second, third = three_commits(tmp_path, monkeypatch)
    repo.create_branch("alias", start_point=third)
    repo.restore(third)
    asset.write_bytes(b"draft")
    repo.save_bud()
    repo.restore(third, discard=True)
    before = database(repo)

    dry = repo.delete_commit(third, dry_run=True)

    assert dry.dry_run is True
    assert database(repo) == before
    assert repo.resolve_commit(third) == third
    assert dry.reclaimable_objects
    assert dry.reclaimable_bytes > 0

    actual = repo.delete_commit(third)
    assert actual.dry_run is False
    for field in (
        "commit",
        "parent_id",
        "moved_branches",
        "moved_current",
        "reconnected_children",
        "rebased_buds",
        "reclaimable_objects",
        "reclaimable_bytes",
    ):
        assert getattr(actual, field) == getattr(dry, field), field
    assert actual.parent_id == second


def test_delete_rolls_back_database_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _asset, _first, second, third = three_commits(tmp_path, monkeypatch)
    with repo.connect() as db:
        db.execute(
            "CREATE TRIGGER fail_delete BEFORE DELETE ON commits "
            "WHEN OLD.id='" + third + "' "
            "BEGIN SELECT RAISE(ABORT, 'simulated delete failure'); END"
        )
    before = database(repo)

    with pytest.raises(SproutError, match="repository unchanged") as exc:
        repo.delete_commit(third)

    assert exc.value.code == "delete_commit_failed"
    assert database(repo) == before
    assert repo.current_commit() == third
    assert repo.head_commit() == third
    with repo.connect() as db:
        db.execute("DROP TRIGGER fail_delete")
    assert repo.doctor().ok
    assert repo.delete_commit(third).parent_id == second


def test_gc_reclaims_objects_of_deleted_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = Repository.init(tmp_path / "project")
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"shared")
    repo.track([asset])
    repo.commit("first")
    asset.write_bytes(b"unique")
    thumbnail = write_image(repo.root / "removed.png", "red")
    removed = repo.commit("removed", thumbnail=thumbnail).commit_id
    removed_hashes = {
        repo.manifest(removed)["asset.bin"].object_hash,
        repo.thumbnail(removed).object_hash,
    }
    asset.write_bytes(b"shared")
    last = repo.commit("last").commit_id
    kept_hash = repo.manifest(last)["asset.bin"].object_hash

    result = repo.delete_commit(removed)
    assert set(result.reclaimable_objects) == removed_hashes
    assert repo.doctor().ok

    gc_result = repo.gc()
    assert set(gc_result.objects) == removed_hashes
    assert all(not (repo.objects / item[:2] / item).exists() for item in removed_hashes)
    assert (repo.objects / kept_hash[:2] / kept_hash).is_file()
    assert repo.doctor().ok


def invoke(args: list[str], cwd: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(cwd)
    return runner.invoke(app, args)


def test_delete_commit_cli_requires_yes_and_supports_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _asset, _first, second, third = three_commits(tmp_path, monkeypatch)
    project = repo.root

    help_result = invoke(["delete-commit", "--help"], project, monkeypatch)
    assert help_result.exit_code == 0
    assert "--dry-run" in help_result.stdout
    assert "--yes" in help_result.stdout

    unconfirmed = invoke(["delete-commit", third], project, monkeypatch)
    assert unconfirmed.exit_code != 0
    assert "irreversible" in str(unconfirmed.exception)
    assert Repository.discover(project).resolve_commit(third) == third

    dry = invoke(["delete-commit", third, "--dry-run", "--json"], project, monkeypatch)
    assert dry.exit_code == 0
    payload = json.loads(dry.stdout)
    assert payload["dry_run"] is True
    assert payload["commit"]["id"] == third
    assert payload["commit"]["message"] == "third"
    assert payload["parent_id"] == second
    assert payload["moved_branches"] == [
        {"id": repo.branch_id(), "name": "main", "current": True}
    ]
    assert payload["moved_current"] is True
    assert payload["reconnected_children"] == []
    assert payload["rebased_buds"] == []
    assert payload["reclaimable_bytes"] > 0
    assert Repository.discover(project).resolve_commit(third) == third

    text = invoke(["delete-commit", third, "--dry-run"], project, monkeypatch)
    assert text.exit_code == 0
    assert "Would delete commit" in text.stdout
    assert "unsaved changes" in text.stdout

    actual = invoke(["delete-commit", third, "--yes", "--json"], project, monkeypatch)
    assert actual.exit_code == 0
    assert json.loads(actual.stdout)["dry_run"] is False
    assert Repository.discover(project).head_commit() == second

    repo.create_tag("keep", second)
    tagged = invoke(["delete-commit", "keep", "--yes", "--json"], project, monkeypatch)
    assert tagged.exit_code != 0
    assert isinstance(tagged.exception, SproutError)
    assert tagged.exception.code == "tagged_commit"
    assert Repository.discover(project).resolve_commit(second) == second
