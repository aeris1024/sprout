import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository

SCRIPT = Path(__file__).parents[1] / "scripts" / "create_sample_repo.py"


def create_sample(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(output)],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    )


@pytest.fixture(scope="module")
def sample(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("sample") / "repo"
    result = create_sample(output)
    assert result.returncode == 0, result.stderr
    return output


@pytest.fixture
def sprout(sample: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(sample)

    def run(*args: str):
        result = CliRunner().invoke(app, [*args, "--json"])
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    return run


def test_sample_contains_each_feature(sprout) -> None:
    tree = sprout("leaf", "tree")
    assert {branch["name"] for branch in tree["branches"]} == {"main", "night", "logo-test"}
    assert {tag["name"] for tag in tree["tags"]} == {"first-draft", "submitted"}
    assert "abandoned" in {commit["branch_name"] for commit in tree["commits"]}
    assert len(tree["buds"]) == 1
    trash = sprout("trash", "list")
    assert len(trash) == 1
    assert sprout("trash", "restore", trash[0]["id"], "--dry-run")["dry_run"] is True

    submitted = sprout("leaf", "show", "submitted")
    assert submitted["thumbnail"] is not None
    assert submitted["note"]
    assert submitted["labels"] == ["submitted"]
    previews = sprout("leaf", "preview", "list", "submitted")
    assert len(previews) == 3
    assert all('is_primary' not in preview for preview in previews)


def test_sample_ends_clean_on_main_with_healthy_storage(sprout, sample: Path) -> None:
    assert sprout("maintenance", "doctor")["ok"] is True
    status = sprout("status", "--untracked")
    assert status["branch"] == "main"
    assert status["at_branch_tip"] is True
    assert status["changes"] == []
    assert status["untracked"] == ["scratch-idea.txt"]
    assert (sample / "GUIDE.md").is_file()


def test_sample_tracks_logo_across_move(sprout) -> None:
    files = {item["path"]: item["file_id"] for item in sprout("leaf", "show", "main")["files"]}
    history = sprout("leaf", "list", "--file-id", files["assets/brand/logo.png"])
    paths = {entry["path"] for entry in history}
    assert {"assets/logo.png", "assets/brand/logo.png"} <= paths


def test_sample_refuses_non_empty_output(tmp_path: Path) -> None:
    keep = tmp_path / "keep.txt"
    keep.write_text("keep", encoding="utf-8")
    result = create_sample(tmp_path)
    assert result.returncode != 0
    assert keep.read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / ".sprout").exists()


def test_gui_canonical_reads_and_thumbnail_export_match_one_shot_and_serve(sprout, sample: Path, tmp_path: Path) -> None:
    """Exercise the same nested argv used by the GUI through real CLI processes."""
    reads = [
        ["status", "--tracked", "--untracked"], ["leaf", "tree"],
        ["leaf", "show", "submitted"], ["file", "diff", "first-draft", "submitted"],
        ["maintenance", "stats"], ["leaf", "label", "list"],
    ]
    requests = [
        {"id": index, "cwd": str(sample), "args": [*args, "--json"]}
        for index, args in enumerate(reads)
    ]
    output = tmp_path / "thumbnail.png"
    requests.append({"id": "thumbnail", "cwd": str(sample), "args": ["leaf", "thumbnail", "export", "submitted", "--output", str(output), "--json"]})
    process = subprocess.run(
        [sys.executable, "-c", "import sys; from sprout.cli import main; sys.exit(main())", "serve"],
        input="\n".join(json.dumps(request) for request in requests) + "\n",
        capture_output=True, encoding="utf-8", cwd=sample,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    assert process.returncode == 0, process.stderr
    replies = [json.loads(line) for line in process.stdout.splitlines()]
    assert replies[0]["ready"] is True
    for args, reply in zip(reads, replies[1:]):
        assert reply["ok"] and reply["exit_code"] == 0, reply
        assert reply["result"] == sprout(*args)
    assert replies[-1]["id"] == "thumbnail" and replies[-1]["ok"], replies[-1]
    assert output.read_bytes().startswith(b"\x89PNG")


def test_gui_canonical_text_arguments_preserve_option_like_values(tmp_path: Path) -> None:
    repo = Repository.init(tmp_path / "text-project")
    asset = repo.root / "asset.txt"
    asset.write_text("first", encoding="utf-8")
    repo.track([asset])
    first = repo.commit("first").commit_id

    def run(*args: str):
        return subprocess.run(
            [sys.executable, "-c", "import sys; from sprout.cli import main; sys.exit(main())", *args],
            cwd=repo.root, capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"},
        )

    def call(*args: str):
        result = run(*args)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    assert call("branch", "comment", "--json", "--", "main", "-comment\nsecond line")["comment"] == "-comment\nsecond line"
    call("leaf", "tag", "create", "keep", first, "--comment=--json", "--json")
    assert call("leaf", "tag", "comment", "--json", "--", "keep", "-comment")["comment"] == "-comment"
    asset.write_text("draft", encoding="utf-8")
    bud = call("bud", "save", "--json")
    assert call("bud", "rename", "--json", "--", bud["id"], "-name")["name"] == "-name"
    assert call("leaf", "edit", first, "--message=--json", "--note=--json", "--json")["message"] == "--json"
    assert repo.annotations(first).note == "--json"
    assert call("leaf", "label", "add", "--json", "--", first, "--json")["labels"] == ["--json"]
    assert call("leaf", "label", "remove", "--json", "--", first, "--json")["labels"] == []
    refused = run("branch", "rename", "--json", "--", "main", "-name")
    assert refused.returncode == 1
    assert json.loads(refused.stderr)["code"] == "invalid_reference_name"
