from pathlib import Path

import typer
from typer.testing import CliRunner

from sprout.cli import app
from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository

runner = CliRunner()


def invoke(args: list[str], cwd: Path, monkeypatch):
    monkeypatch.chdir(cwd)
    return runner.invoke(app, args)


def test_cli_workflow(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    result = invoke(["init", str(project)], tmp_path, monkeypatch)
    assert result.exit_code == 0
    asset = project / "scene.blend"
    asset.write_bytes(b"scene")

    assert invoke(["track", "scene.blend"], project, monkeypatch).exit_code == 0
    result = invoke(["status"], project, monkeypatch)
    assert "added" in result.stdout
    result = invoke(["commit", "-m", "first"], project, monkeypatch)
    assert result.exit_code == 0
    assert "[main " in result.stdout
    assert "Working tree clean" in invoke(["status"], project, monkeypatch).stdout
    result = invoke(["status", "scene.blend"], project, monkeypatch)
    assert "tracked   scene.blend" in result.stdout
    untracked = project / "notes.txt"
    untracked.write_text("memo")
    result = invoke(["status", "notes.txt"], project, monkeypatch)
    assert "untracked notes.txt" in result.stdout
    result = invoke(["status", "--tracked"], project, monkeypatch)
    assert "Tracked files:" in result.stdout
    assert "scene.blend" in result.stdout
    result = invoke(["status", "--untracked"], project, monkeypatch)
    assert "Untracked files:" in result.stdout
    assert "notes.txt" in result.stdout
    assert "scene.blend" not in result.stdout
    result = invoke(["move", "scene.blend", "archive/scene.blend"], project, monkeypatch)
    assert result.exit_code == 0
    assert "move  scene.blend -> archive/scene.blend" in result.stdout
    assert not asset.exists()
    assert (project / "archive/scene.blend").read_bytes() == b"scene"
    assert "first" in invoke(["log"], project, monkeypatch).stdout
    assert "* main" in invoke(["branch"], project, monkeypatch).stdout
    result = invoke(["branch", "ideas", "--comment", "Explore silhouettes"], project, monkeypatch)
    assert result.exit_code == 0
    assert "Explore silhouettes" in invoke(["branch"], project, monkeypatch).stdout
    result = invoke(["branch", "ideas", "--set-comment", "Explore colors"], project, monkeypatch)
    assert result.exit_code == 0
    assert "Explore colors" in invoke(["branch"], project, monkeypatch).stdout


def test_main_formats_operating_system_errors(monkeypatch, capsys) -> None:
    def fail(**kwargs) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(cli, "app", fail)
    assert cli.main() == 1
    assert "repository operation failed: disk full" in capsys.readouterr().err


def test_main_returns_zero_on_success(monkeypatch) -> None:
    def succeed(**kwargs) -> None:
        assert kwargs == {"standalone_mode": False}

    monkeypatch.setattr(cli, "app", succeed)
    assert cli.main() == 0


def test_main_returns_click_exit_code(monkeypatch) -> None:
    def exit_cleanly(**kwargs) -> None:
        raise typer.Exit(0)

    monkeypatch.setattr(cli, "app", exit_cleanly)
    assert cli.main() == 0


def test_main_handles_click_like_usage_errors(monkeypatch) -> None:
    class FakeClickException(Exception):
        exit_code = 2

        def __init__(self) -> None:
            self.shown = False

        def show(self) -> None:
            self.shown = True

    error = FakeClickException()

    def fail(**kwargs) -> None:
        raise error

    monkeypatch.setattr(cli, "app", fail)
    assert cli.main() == 2
    assert error.shown is True


def test_main_reraises_unknown_exceptions(monkeypatch) -> None:
    class UnknownError(Exception):
        pass

    def fail(**kwargs) -> None:
        raise UnknownError("boom")

    monkeypatch.setattr(cli, "app", fail)
    try:
        cli.main()
    except UnknownError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("unknown exception was swallowed")


def test_main_normalizes_non_integer_system_exit(monkeypatch) -> None:
    def fail(**kwargs) -> None:
        raise SystemExit("message")

    monkeypatch.setattr(cli, "app", fail)
    assert cli.main() == 1


def test_main_formats_sprout_errors(monkeypatch, capsys) -> None:
    def fail(**kwargs) -> None:
        raise SproutError("bad branch")

    monkeypatch.setattr(cli, "app", fail)
    assert cli.main() == 1
    assert "Error: bad branch" in capsys.readouterr().err


def test_status_path_mode_rejects_listing_flags(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "scene.blend"
    asset.write_bytes(b"scene")

    result = invoke(["status", "scene.blend", "--tracked"], project, monkeypatch)
    assert result.exit_code != 0
    assert "path status cannot be combined" in str(result.exception)


def test_move_rejects_untracked_source(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    (project / "draft.txt").write_text("draft")

    result = invoke(["move", "draft.txt", "archive/draft.txt"], project, monkeypatch)
    assert result.exit_code != 0
    assert "path is not tracked" in str(result.exception)


def test_discard_help_describes_tracked_and_untracked_behavior(
    tmp_path: Path, monkeypatch
) -> None:
    result = invoke(["switch", "--help"], tmp_path, monkeypatch)
    assert result.exit_code == 0
    help_text = " ".join(result.stdout.split())
    assert "Discard all tracked changes" in help_text
    assert "untracked" in help_text
    assert "untouched" in help_text

    result = invoke(["restore", "--help"], tmp_path, monkeypatch)
    assert result.exit_code == 0
    help_text = " ".join(result.stdout.split())
    assert "Discard tracked changes on restored paths" in help_text
    assert "untouched" in help_text


def test_gc_cli_reports_removed_objects_and_supports_dry_run(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"kept")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "initial"], project, monkeypatch).exit_code == 0

    orphan_hash = "ef" + ("2" * 62)
    orphan = project / ".sprout" / "objects" / orphan_hash[:2] / orphan_hash
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"gone")
    stale_temp = project / ".sprout" / "tmp" / "object-cli"
    stale_temp.write_bytes(b"tmp")

    dry = invoke(["gc", "--dry-run"], project, monkeypatch)
    assert dry.exit_code == 0
    assert f"object  {orphan_hash}" in dry.stdout
    assert "temp    object-cli" in dry.stdout
    assert "Would remove 1 objects, 1 temp files (7 bytes)" in dry.stdout
    assert orphan.is_file()
    assert stale_temp.is_file()

    result = invoke(["gc"], project, monkeypatch)
    assert result.exit_code == 0
    assert "Removed 1 objects, 1 temp files (7 bytes)" in result.stdout
    assert not orphan.exists()
    assert not stale_temp.exists()


def test_doctor_cli_reports_ok_and_issues(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"data")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "initial"], project, monkeypatch).exit_code == 0

    healthy = invoke(["doctor"], project, monkeypatch)
    assert healthy.exit_code == 0
    assert "OK (1 objects checked)" in healthy.stdout

    repo = Repository.discover(project)
    object_hash = repo.manifest(repo.head_commit())["asset.bin"].object_hash
    (repo.objects / object_hash[:2] / object_hash).unlink()

    broken = invoke(["doctor"], project, monkeypatch)
    assert broken.exit_code == 1
    assert f"missing_object     {object_hash}" in broken.stdout
    assert "Found 1 issue(s) (1 objects checked)" in broken.stdout
    assert asset.read_bytes() == b"data"


def test_partial_restore_cli(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    first = project / "first.bin"
    second = project / "second.bin"
    first.write_bytes(b"v1")
    second.write_bytes(b"v1")
    assert invoke(["track", "first.bin", "second.bin"], project, monkeypatch).exit_code == 0
    result = invoke(["commit", "-m", "old"], project, monkeypatch)
    assert result.exit_code == 0
    commit_id = result.stdout.split()[1].rstrip("]")
    first.write_bytes(b"v2")
    second.write_bytes(b"v2")
    assert invoke(["commit", "-m", "new"], project, monkeypatch).exit_code == 0

    restored = invoke(["restore", commit_id, "first.bin"], project, monkeypatch)
    assert restored.exit_code == 0
    assert "Restored paths from" in restored.stdout
    assert first.read_bytes() == b"v1"
    assert second.read_bytes() == b"v2"


def test_diff_cli_shows_commit_and_working_tree_changes(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    first = invoke(["commit", "-m", "first"], project, monkeypatch)
    assert first.exit_code == 0
    first_id = first.stdout.split()[1].rstrip("]")
    asset.write_bytes(b"v2xx")
    assert invoke(["commit", "-m", "second"], project, monkeypatch).exit_code == 0

    between = invoke(["diff", first_id, "main"], project, monkeypatch)
    assert between.exit_code == 0
    assert "modified asset.bin  (2 bytes -> 4 bytes)" in between.stdout

    asset.write_bytes(b"work")
    working = invoke(["diff"], project, monkeypatch)
    assert working.exit_code == 0
    assert "modified asset.bin  (4 bytes -> 4 bytes)" in working.stdout


def test_log_path_cli_filters_history(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    target = project / "target.bin"
    other = project / "other.bin"
    target.write_bytes(b"v1")
    other.write_bytes(b"other")
    assert invoke(["track", "target.bin", "other.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "add both"], project, monkeypatch).exit_code == 0
    other.write_bytes(b"other2")
    assert invoke(["commit", "-m", "change other"], project, monkeypatch).exit_code == 0
    target.write_bytes(b"v2")
    assert invoke(["commit", "-m", "change target"], project, monkeypatch).exit_code == 0

    result = invoke(["log", "target.bin"], project, monkeypatch)
    assert result.exit_code == 0
    assert "change target" in result.stdout
    assert "add both" in result.stdout
    assert "change other" not in result.stdout

    missing = invoke(["log", "missing.bin"], project, monkeypatch)
    assert missing.exit_code == 0
    assert "No history for path: missing.bin" in missing.stdout
