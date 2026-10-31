import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sprout.cli import app

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
    tree = sprout("tree")
    assert {branch["name"] for branch in tree["branches"]} == {"main", "night", "logo-test"}
    assert {tag["name"] for tag in tree["tags"]} == {"first-draft", "submitted"}
    assert "abandoned" in {commit["branch_name"] for commit in tree["commits"]}
    assert len(tree["buds"]) == 1
    trash = sprout("trash", "list")
    assert len(trash) == 1
    assert sprout("trash", "restore", trash[0]["id"], "--dry-run")["dry_run"] is True

    submitted = sprout("show", "submitted")
    assert submitted["thumbnail"] is not None
    assert submitted["note"]
    assert submitted["labels"] == ["submitted"]
    previews = sprout("preview", "list", "submitted")
    assert len(previews) == 3
    assert all('is_primary' not in preview for preview in previews)


def test_sample_ends_clean_on_main_with_healthy_storage(sprout, sample: Path) -> None:
    assert sprout("doctor")["ok"] is True
    status = sprout("status", "--untracked")
    assert status["branch"] == "main"
    assert status["at_branch_tip"] is True
    assert status["changes"] == []
    assert status["untracked"] == ["scratch-idea.txt"]
    assert (sample / "GUIDE.md").is_file()


def test_sample_tracks_logo_across_move(sprout) -> None:
    files = {item["path"]: item["file_id"] for item in sprout("show", "main")["files"]}
    history = sprout("file-history", files["assets/brand/logo.png"])
    paths = {entry["path"] for entry in history}
    assert {"assets/logo.png", "assets/brand/logo.png"} <= paths


def test_sample_refuses_non_empty_output(tmp_path: Path) -> None:
    keep = tmp_path / "keep.txt"
    keep.write_text("keep", encoding="utf-8")
    result = create_sample(tmp_path)
    assert result.returncode != 0
    assert keep.read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / ".sprout").exists()
