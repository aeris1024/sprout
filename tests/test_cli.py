from pathlib import Path

import typer
from typer.testing import CliRunner

from sprout.cli import app
from sprout import cli
from sprout.errors import SproutError

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
