import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import typer
import typer.completion as typer_completion
from PIL import Image
from typer.testing import CliRunner

from sprout.cli import app
from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository

runner = CliRunner()


def invoke(args: list[str], cwd: Path, monkeypatch):
    monkeypatch.chdir(cwd)
    return runner.invoke(app, args)


def write_image(path: Path, image_format: str = "PNG", color: str = "navy") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 12), color).save(path, format=image_format)
    return path


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


def test_branch_cli_renames_and_deletes(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    (project / "asset.bin").write_bytes(b"data")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    assert invoke(["branch", "experiment", "-m", "案"], project, monkeypatch).exit_code == 0

    renamed = invoke(
        ["branch", "experiment", "--rename", "prototype"], project, monkeypatch
    )
    assert renamed.exit_code == 0
    assert renamed.stdout == "Renamed branch experiment to prototype\n"
    branches = json.loads(invoke(["branch", "--json"], project, monkeypatch).stdout)
    assert any(
        branch["name"] == "prototype" and branch["comment"] == "案"
        for branch in branches
    )
    assert all(branch["name"] != "experiment" for branch in branches)

    deleted = invoke(["branch", "--delete", "prototype"], project, monkeypatch)
    assert deleted.exit_code == 0
    assert deleted.stdout == "Deleted branch prototype\n"
    assert "prototype" not in invoke(["branch"], project, monkeypatch).stdout

    current = invoke(["branch", "--delete", "main"], project, monkeypatch)
    assert current.exit_code != 0
    assert "cannot delete current branch" in str(current.exception)

    conflict = invoke(
        ["branch", "main", "--rename", "trunk", "--set-comment", "note"],
        project,
        monkeypatch,
    )
    assert conflict.exit_code != 0
    assert "--rename cannot be combined with comment options" in str(conflict.exception)


def test_branch_cli_start_point_switch_and_restored_guard(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    first = Repository.discover().log()[0]["id"]
    asset.write_bytes(b"v2")
    assert invoke(["commit", "-m", "second"], project, monkeypatch).exit_code == 0
    assert invoke(["tag", "landmark", first], project, monkeypatch).exit_code == 0
    assert invoke(["branch", "side"], project, monkeypatch).exit_code == 0
    assert invoke(["switch", "side"], project, monkeypatch).exit_code == 0
    asset.write_bytes(b"side")
    assert invoke(["commit", "-m", "side"], project, monkeypatch).exit_code == 0
    side = Repository.discover().log()[0]["id"]
    assert invoke(["switch", "main"], project, monkeypatch).exit_code == 0

    created = invoke(["branch", "from-commit", first], project, monkeypatch)
    assert created.exit_code == 0
    assert created.stdout == "Created branch from-commit\n"
    assert invoke(["branch", "from-prefix", first[:8]], project, monkeypatch).exit_code == 0
    assert invoke(["branch", "from-tag", "landmark"], project, monkeypatch).exit_code == 0
    assert invoke(["branch", "from-side", "side"], project, monkeypatch).exit_code == 0

    branches = {
        item["name"]: item["commit_id"]
        for item in json.loads(invoke(["branch", "--json"], project, monkeypatch).stdout)
    }
    assert branches["from-commit"] == first
    assert branches["from-prefix"] == first
    assert branches["from-tag"] == first
    assert branches["from-side"] == side

    switched = invoke(
        ["branch", "rethink", first, "--switch"], project, monkeypatch
    )
    assert switched.exit_code == 0
    assert switched.stdout == "Created and switched to branch rethink\n"
    assert Repository.discover().head_branch() == "rethink"
    assert asset.read_bytes() == b"v1"

    assert invoke(["switch", "main"], project, monkeypatch).exit_code == 0
    assert invoke(["restore", first], project, monkeypatch).exit_code == 0
    guarded = invoke(["branch", "oops"], project, monkeypatch)
    assert guarded.exit_code != 0
    assert "specify the start point explicitly" in str(guarded.exception)
    assert "oops" not in invoke(["branch"], project, monkeypatch).stdout

    help_result = invoke(["branch", "--help"], project, monkeypatch)
    assert help_result.exit_code == 0
    help_text = " ".join(help_result.stdout.split())
    assert "START_POINT" in help_text or "start_point" in help_text
    assert "--switch" in help_text
    assert "Commit ID, prefix, branch, or tag" in help_text


def test_tag_cli_creates_lists_resolves_and_deletes(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    first = Repository.discover().log()[0]["id"]
    asset.write_bytes(b"v2")
    assert invoke(["commit", "-m", "second"], project, monkeypatch).exit_code == 0
    second = Repository.discover().log()[0]["id"]

    created = invoke(
        ["tag", "first-draft", first, "-m", "初稿"], project, monkeypatch
    )
    assert created.exit_code == 0
    assert created.stdout == f"Created tag first-draft at {first[:12]}\n"
    latest = invoke(["tag", "submitted"], project, monkeypatch)
    assert latest.exit_code == 0
    assert latest.stdout == f"Created tag submitted at {second[:12]}\n"

    listed = invoke(["tag"], project, monkeypatch)
    assert listed.exit_code == 0
    assert f"first-draft          {first[:12]}  # 初稿" in listed.stdout
    assert f"submitted            {second[:12]}" in listed.stdout

    shown = invoke(["show", "first-draft", "--json"], project, monkeypatch)
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["id"] == first
    restored = invoke(["restore", "first-draft"], project, monkeypatch)
    assert restored.exit_code == 0
    assert asset.read_bytes() == b"v1"

    deleted = invoke(["tag", "--delete", "first-draft"], project, monkeypatch)
    assert deleted.exit_code == 0
    assert deleted.stdout == "Deleted tag first-draft\n"
    assert "first-draft" not in invoke(["tag"], project, monkeypatch).stdout


def test_track_and_untrack_warn_when_nothing_matches(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    (project / "empty").mkdir()

    track_result = invoke(["track", "empty"], project, monkeypatch)
    assert track_result.exit_code == 0
    assert track_result.stdout == ""
    assert "Warning: no files were tracked" in track_result.stderr

    untrack_result = invoke(["untrack", "missing.txt"], project, monkeypatch)
    assert untrack_result.exit_code == 0
    assert untrack_result.stdout == ""
    assert "Warning: no matching tracked paths" in untrack_result.stderr


def test_track_and_untrack_keep_success_output(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    (project / "scene.blend").write_bytes(b"scene")

    track_result = invoke(["track", "scene.blend"], project, monkeypatch)
    assert track_result.exit_code == 0
    assert track_result.stdout == "track  scene.blend\n"
    assert track_result.stderr == ""

    untrack_result = invoke(["untrack", "scene.blend"], project, monkeypatch)
    assert untrack_result.exit_code == 0
    assert untrack_result.stdout == "untrack  scene.blend\n"
    assert untrack_result.stderr == ""


def test_commit_reports_files_removed_from_tracking(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "scene.blend"
    asset.write_bytes(b"scene")
    assert invoke(["track", "scene.blend"], project, monkeypatch).exit_code == 0

    initial = invoke(["commit", "-m", "initial"], project, monkeypatch)
    assert initial.exit_code == 0
    assert len(initial.stdout.splitlines()) == 1
    assert initial.stdout.startswith("[main ")

    asset.unlink()
    removed = invoke(["commit", "-m", "remove scene"], project, monkeypatch)
    assert removed.exit_code == 0
    lines = removed.stdout.splitlines()
    assert len(lines) == 2
    assert lines[0] == "deleted  scene.blend"
    assert lines[1].startswith("[main ")
    assert lines[1].endswith("] remove scene")


def test_show_formats_timestamps_and_supports_timezones(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "scene.blend"
    asset.write_bytes(b"scene")
    mtime_ns = 1_704_067_200_123_456_789
    os.utime(asset, ns=(mtime_ns, mtime_ns))
    stored_mtime_ns = asset.stat().st_mtime_ns
    assert invoke(["track", "scene.blend"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0

    repository = Repository.discover()
    commit_row = repository.log()[0]
    commit_id = commit_row["id"]
    _, files = repository.commit_info(commit_id)
    assert files[0].mtime_ns == stored_mtime_ns

    utc_result = invoke(["show", commit_id], project, monkeypatch)
    assert utc_result.exit_code == 0
    assert "Date:   " in utc_result.stdout
    assert " UTC\n" in utc_result.stdout
    assert "2024-01-01 00:00:00 UTC  scene.blend" in utc_result.stdout
    assert str(stored_mtime_ns) not in utc_result.stdout

    tokyo_result = invoke(
        ["show", commit_id, "--timezone", "Asia/Tokyo"], project, monkeypatch
    )
    assert tokyo_result.exit_code == 0
    created_at = datetime.fromisoformat(commit_row["created_at"])
    expected_created_at = created_at.astimezone(ZoneInfo("Asia/Tokyo"))
    assert f"Date:   {expected_created_at:%Y-%m-%d %H:%M:%S} JST" in tokyo_result.stdout
    assert "2024-01-01 09:00:00 JST  scene.blend" in tokyo_result.stdout

    local_result = invoke(["show", commit_id, "--timezone", "local"], project, monkeypatch)
    assert local_result.exit_code == 0
    assert str(stored_mtime_ns) not in local_result.stdout


def test_show_rejects_unknown_timezone(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    (project / "scene.blend").write_bytes(b"scene")
    assert invoke(["track", "scene.blend"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    commit_id = Repository.discover().log()[0]["id"]

    result = invoke(["show", commit_id, "--timezone", "Mars/Olympus"], project, monkeypatch)
    assert result.exit_code != 0
    assert "unknown timezone: Mars/Olympus" in str(result.exception)


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


def test_progress_display_requires_tty_and_large_file(monkeypatch) -> None:
    created: list[dict[str, object]] = []

    class Stream:
        def __init__(self, tty: bool):
            self.tty = tty

        def isatty(self) -> bool:
            return self.tty

    class Bar:
        def __init__(self, **kwargs):
            self.record = {"kwargs": kwargs, "updates": [], "entered": 0, "exited": 0}
            created.append(self.record)

        def __enter__(self):
            self.record["entered"] += 1
            return self

        def __exit__(self, *_args):
            self.record["exited"] += 1

        def update(self, amount: int) -> None:
            self.record["updates"].append(amount)

    monkeypatch.setattr(cli.typer, "progressbar", lambda **kwargs: Bar(**kwargs))

    monkeypatch.setattr(cli.sys, "stderr", Stream(False))
    redirected = cli._ProgressDisplay()
    redirected("large.bin", cli.PROGRESS_THRESHOLD, cli.PROGRESS_THRESHOLD)
    assert created == []

    monkeypatch.setattr(cli.sys, "stderr", Stream(True))
    terminal = cli._ProgressDisplay()
    terminal("small.bin", 10, 10)
    assert created == []

    terminal(
        "large.bin",
        cli.PROGRESS_THRESHOLD // 2,
        cli.PROGRESS_THRESHOLD,
    )
    terminal(
        "large.bin",
        cli.PROGRESS_THRESHOLD,
        cli.PROGRESS_THRESHOLD,
    )
    assert len(created) == 1
    assert created[0]["updates"] == [
        cli.PROGRESS_THRESHOLD // 2,
        cli.PROGRESS_THRESHOLD // 2,
    ]
    assert created[0]["entered"] == 1
    assert created[0]["exited"] == 1


def test_completion_scripts_and_install_callback(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION", "1")
    expected_markers = {
        "powershell": "complete_powershell",
        "bash": "complete_bash",
        "zsh": "complete_zsh",
    }
    for shell, marker in expected_markers.items():
        result = invoke(["--show-completion", shell], tmp_path, monkeypatch)
        assert result.exit_code == 0
        assert marker in result.stdout
        if shell == "powershell":
            assert "try {" in result.stdout
            assert "finally {" in result.stdout
            assert "Remove-Item Env:_ROOT_COMPLETE" in result.stdout
            assert "$previousComplete" in result.stdout

    installed: list[str] = []

    def fake_install(shell: str | None = None):
        installed.append(getattr(shell, "value", str(shell)))
        return "powershell", tmp_path / "Microsoft.PowerShell_profile.ps1"

    monkeypatch.setattr(typer_completion, "install", fake_install)
    result = invoke(["--install-completion", "powershell"], tmp_path, monkeypatch)
    assert result.exit_code == 0
    assert installed == ["powershell"]
    assert "powershell completion installed" in result.stdout
    assert "restart the terminal" in result.stdout

    monkeypatch.setattr(sys, "argv", ["sprout", "--show-completion", "bash"])
    assert cli.main() == 0
    assert "complete_bash" in capsys.readouterr().out


def test_main_recovers_from_stale_powershell_completion_environment(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    project = tmp_path / "project"
    Repository.init(project)
    monkeypatch.chdir(project)
    monkeypatch.setattr(sys, "argv", ["sprout", "status"])
    monkeypatch.setenv("_SPROUT_COMPLETE", "complete_powershell")
    monkeypatch.setenv("_TYPER_COMPLETE_ARGS", "sprout branch .\\")
    monkeypatch.setenv("_TYPER_COMPLETE_WORD_TO_COMPLETE", ".\\")

    assert cli.main() == 0
    assert "Working tree clean" in capsys.readouterr().out
    for name in cli._COMPLETION_ENVIRONMENT_VARIABLES:
        assert name not in os.environ


def test_completion_environment_is_preserved_for_real_completion_invocation(
    monkeypatch,
) -> None:
    monkeypatch.setenv("_SPROUT_COMPLETE", "complete_powershell")
    monkeypatch.setenv("_TYPER_COMPLETE_ARGS", "sprout branch .\\")
    monkeypatch.setenv("_TYPER_COMPLETE_WORD_TO_COMPLETE", ".\\")

    cli._clear_stale_completion_environment(["sprout"])

    assert os.environ["_SPROUT_COMPLETE"] == "complete_powershell"
    assert os.environ["_TYPER_COMPLETE_ARGS"] == "sprout branch .\\"
    assert os.environ["_TYPER_COMPLETE_WORD_TO_COMPLETE"] == ".\\"


def test_dynamic_completion_returns_refs_and_is_safe_outside_repository(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli._complete_branches() == []
    assert cli._complete_references() == []

    project = tmp_path / "project"
    repository = Repository.init(project)
    monkeypatch.chdir(project)
    asset = project / "asset.bin"
    asset.write_bytes(b"data")
    repository.track([asset])
    repository.commit("first")
    repository.create_branch("experiment")
    repository.create_tag("submitted")

    assert cli._complete_branches() == ["experiment", "main"]
    assert cli._complete_references() == ["experiment", "main", "submitted"]


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


def test_stats_cli_shows_counts_and_dedup(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    twin = project / "twin.bin"
    asset.write_bytes(b"abcd")
    twin.write_bytes(b"abcd")
    assert invoke(["track", "asset.bin", "twin.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "shared"], project, monkeypatch).exit_code == 0

    result = invoke(["stats"], project, monkeypatch)
    assert result.exit_code == 0
    assert "Commits:       1" in result.stdout
    assert "Branches:      1" in result.stdout
    assert "Tracked paths: 2" in result.stdout
    object_bytes = sum(
        path.stat().st_size
        for path in (project / ".sprout" / "objects").glob("*/*")
    )
    assert f"Objects:       1 ({object_bytes} bytes)" in result.stdout
    assert "Logical size:  8 bytes" in result.stdout
    assert "Unique size:   4 bytes" in result.stdout
    assert "Dedup saved:   4 bytes" in result.stdout
    assert asset.read_bytes() == b"abcd"


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


def test_export_and_cat_cli(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "assets" / "image.bin"
    asset.parent.mkdir()
    content = b"\x00\xffold-image\r\n"
    asset.write_bytes(content)
    saved_mtime = 1_700_000_000_123_456_700
    os.utime(asset, ns=(saved_mtime, saved_mtime))
    assert invoke(["track", "assets/image.bin"], project, monkeypatch).exit_code == 0
    committed = invoke(["commit", "-m", "saved"], project, monkeypatch)
    assert committed.exit_code == 0
    commit_id = committed.stdout.split()[1].rstrip("]")
    asset.write_bytes(b"working")

    output = tmp_path / "exported"
    exported = invoke(
        ["export", commit_id, "assets", "--output", str(output)],
        project,
        monkeypatch,
    )
    assert exported.exit_code == 0
    assert "export  assets/image.bin" in exported.stdout
    exported_file = output / "assets" / "image.bin"
    assert exported_file.read_bytes() == content
    assert exported_file.stat().st_mtime_ns == saved_mtime
    assert asset.read_bytes() == b"working"
    assert Repository.discover(project).tracked() == {"assets/image.bin"}

    duplicate = invoke(
        ["export", commit_id, "--output", str(output)],
        project,
        monkeypatch,
    )
    assert duplicate.exit_code != 0
    assert "output file already exists" in str(duplicate.exception)
    assert exported_file.read_bytes() == content

    forced = invoke(
        ["export", commit_id, "--output", str(output), "--force"],
        project,
        monkeypatch,
    )
    assert forced.exit_code == 0
    assert exported_file.read_bytes() == content

    cat_result = invoke(["cat", commit_id, "assets/image.bin"], project, monkeypatch)
    assert cat_result.exit_code == 0
    assert cat_result.stdout_bytes == content
    assert asset.read_bytes() == b"working"


def test_thumbnail_cli_commit_show_replace_export_and_delete(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"data")
    first = write_image(tmp_path / "first.png")
    second = write_image(tmp_path / "second.webp", "WEBP", "green")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0

    committed = invoke(
        ["commit", "-m", "with thumbnail", "--thumbnail", str(first)],
        project,
        monkeypatch,
    )
    assert committed.exit_code == 0
    commit_id = Repository.discover(project).head_commit()
    assert commit_id is not None

    shown = invoke(["show", commit_id], project, monkeypatch)
    assert shown.exit_code == 0
    assert "Thumbnail: first.png (image/png" in shown.stdout
    payload = json.loads(
        invoke(["show", commit_id, "--json"], project, monkeypatch).stdout
    )
    assert payload["thumbnail"]["role"] == "thumbnail"
    assert payload["thumbnail"]["original_name"] == "first.png"
    inspected = json.loads(
        invoke(["thumbnail", commit_id, "--json"], project, monkeypatch).stdout
    )
    assert inspected == payload["thumbnail"]

    replaced = invoke(["thumbnail", commit_id, str(second)], project, monkeypatch)
    assert replaced.exit_code == 0
    assert "Set thumbnail" in replaced.stdout
    output = tmp_path / "exported.webp"
    exported = invoke(
        ["thumbnail", commit_id, "--output", str(output)], project, monkeypatch
    )
    assert exported.exit_code == 0
    assert output.read_bytes() == second.read_bytes()

    deleted = invoke(["thumbnail", commit_id, "--delete"], project, monkeypatch)
    assert deleted.exit_code == 0
    assert json.loads(
        invoke(["thumbnail", commit_id, "--json"], project, monkeypatch).stdout
    ) is None


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


def test_log_cli_limits_and_summarizes_history(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    commit_ids: list[str] = []
    for version in ("first", "second", "third"):
        asset.write_text(version)
        result = invoke(["commit", "-m", version], project, monkeypatch)
        assert result.exit_code == 0
        commit_ids.append(Repository.discover().log()[0]["id"])

    limited = invoke(["log", "-n", "2"], project, monkeypatch)
    assert limited.exit_code == 0
    assert "third" in limited.stdout
    assert "second" in limited.stdout
    assert "first" not in limited.stdout

    full = invoke(["log"], project, monkeypatch)
    assert full.exit_code == 0
    assert all(message in full.stdout for message in ("first", "second", "third"))

    oneline = invoke(["log", "--max-count", "2", "--oneline"], project, monkeypatch)
    assert oneline.exit_code == 0
    assert oneline.stdout.splitlines() == [
        f"{commit_ids[2][:12]} third",
        f"{commit_ids[1][:12]} second",
    ]

    invalid = invoke(["log", "-n", "0"], project, monkeypatch)
    assert invalid.exit_code != 0
    assert "x>=1" in invalid.stderr


def test_note_and_label_cli_updates_displays_and_filters_annotations(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    first_id = Repository.discover().log()[0]["id"]

    note_set = invoke(["note", first_id, "  client approved  "], project, monkeypatch)
    assert note_set.exit_code == 0
    note_show = invoke(["note", first_id], project, monkeypatch)
    assert "client approved" in note_show.stdout
    assert "Updated:" in note_show.stdout

    assert invoke(["label", first_id, " Approved "], project, monkeypatch).exit_code == 0
    assert invoke(["label", first_id, "approved"], project, monkeypatch).exit_code == 0
    labels = invoke(["label", first_id], project, monkeypatch)
    assert labels.stdout.splitlines() == ["Approved", "approved"]

    asset.write_bytes(b"v2")
    assert invoke(["commit", "-m", "second"], project, monkeypatch).exit_code == 0
    second_id = Repository.discover().log()[0]["id"]
    assert invoke(["label", second_id, "Other"], project, monkeypatch).exit_code == 0

    filtered = invoke(["log", "--label", " Approved "], project, monkeypatch)
    assert filtered.exit_code == 0
    assert "first" in filtered.stdout
    assert "second" not in filtered.stdout
    assert "Labels: Approved, approved" in filtered.stdout
    assert "Note:   client approved" in filtered.stdout
    assert "Note updated:" in filtered.stdout

    show_payload = json.loads(
        invoke(["show", first_id, "--json"], project, monkeypatch).stdout
    )
    assert show_payload["note"] == "client approved"
    assert show_payload["note_updated_at"] is not None
    assert show_payload["labels"] == ["Approved", "approved"]
    log_payload = json.loads(
        invoke(["log", "--label", "Approved", "--json"], project, monkeypatch).stdout
    )
    assert len(log_payload) == 1
    assert log_payload[0]["id"] == first_id
    assert log_payload[0]["note"] == "client approved"
    assert log_payload[0]["labels"] == ["Approved", "approved"]

    assert invoke(
        ["label", first_id, "--delete", "Approved"], project, monkeypatch
    ).exit_code == 0
    assert invoke(["label", first_id], project, monkeypatch).stdout == "approved\n"
    assert invoke(["note", first_id, "replaced"], project, monkeypatch).exit_code == 0
    shown = invoke(["show", first_id], project, monkeypatch).stdout
    assert "replaced" in shown
    assert "Note updated:" in shown
    assert invoke(["note", first_id, "--delete"], project, monkeypatch).exit_code == 0
    assert invoke(["note", first_id], project, monkeypatch).stdout == "No note\n"


def test_note_and_label_cli_reject_conflicting_or_invalid_input(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"data")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    commit_id = Repository.discover().log()[0]["id"]

    conflict = invoke(["note", commit_id, "text", "--delete"], project, monkeypatch)
    assert conflict.exit_code != 0
    assert "cannot be combined" in str(conflict.exception)
    conflict = invoke(
        ["label", commit_id, "value", "--delete", "other"], project, monkeypatch
    )
    assert conflict.exit_code != 0
    assert "cannot be combined" in str(conflict.exception)
    invalid = invoke(["label", commit_id, "   "], project, monkeypatch)
    assert invalid.exit_code != 0
    assert "label cannot be empty" in str(invalid.exception)


def test_tree_cli_shows_complete_graph_and_structured_json(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    first = Repository.discover().log()[0]["id"]
    asset.write_bytes(b"main-v2")
    assert invoke(["commit", "-m", "main work"], project, monkeypatch).exit_code == 0
    main_tip = Repository.discover().log()[0]["id"]

    assert invoke(
        ["branch", "side", first, "--switch"], project, monkeypatch
    ).exit_code == 0
    asset.write_bytes(b"side-v2")
    assert invoke(["commit", "-m", "side work"], project, monkeypatch).exit_code == 0
    side_tip = Repository.discover().log()[0]["id"]
    thumbnail = write_image(project / "preview.png")
    assert invoke(["thumbnail", side_tip, str(thumbnail)], project, monkeypatch).exit_code == 0
    assert invoke(["note", side_tip, "review this"], project, monkeypatch).exit_code == 0
    assert invoke(["label", side_tip, "Candidate"], project, monkeypatch).exit_code == 0
    assert invoke(["switch", "main"], project, monkeypatch).exit_code == 0
    assert invoke(["branch", "archive", first], project, monkeypatch).exit_code == 0
    assert invoke(["tag", "baseline", first, "-m", "shared root"], project, monkeypatch).exit_code == 0
    assert invoke(["branch", "--delete", "side"], project, monkeypatch).exit_code == 0

    human = invoke(["tree"], project, monkeypatch)
    assert human.exit_code == 0
    assert f"* {first[:12]} first" in human.stdout
    assert f"{main_tip[:12]} main work" in human.stdout
    assert f"{side_tip[:12]} side work" in human.stdout
    assert "|- *" in human.stdout
    assert "`- *" in human.stdout
    assert "[created:main]" in human.stdout
    assert "[branch:archive]" in human.stdout
    assert "[branch:*main]" in human.stdout
    assert "[tag:baseline]" in human.stdout
    assert "[created:side]" in human.stdout
    assert "[branch:side]" not in human.stdout
    assert "[thumbnail]" in human.stdout
    assert "[note]" in human.stdout
    assert "[labels:Candidate]" in human.stdout

    result = invoke(["tree", "--json"], project, monkeypatch)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert [commit["id"] for commit in payload["commits"]] == [
        side_tip,
        main_tip,
        first,
    ]
    commits = {commit["id"]: commit for commit in payload["commits"]}
    assert set(commits) == {first, main_tip, side_tip}
    assert commits[side_tip]["parent_id"] == first
    assert commits[side_tip]["branch_name"] == "side"
    assert commits[side_tip]["message"] == "side work"
    assert commits[side_tip]["note"] == "review this"
    assert commits[side_tip]["note_updated_at"] is not None
    assert commits[side_tip]["labels"] == ["Candidate"]
    assert len(commits[side_tip]["attachments"]) == 1
    attachment = commits[side_tip]["attachments"][0]
    assert attachment["commit_id"] == side_tip
    assert attachment["role"] == "thumbnail"
    assert attachment["original_name"] == "preview.png"
    assert attachment["media_type"] == "image/png"
    assert attachment["size"] > 0
    assert attachment["created_at"]
    assert attachment["updated_at"]
    assert payload["branches"] == [
        {"name": "archive", "commit_id": first, "comment": "", "current": False},
        {"name": "main", "commit_id": main_tip, "comment": "", "current": True},
    ]
    assert len(payload["tags"]) == 1
    assert payload["tags"][0]["name"] == "baseline"
    assert payload["tags"][0]["commit_id"] == first
    assert payload["tags"][0]["comment"] == "shared root"
    assert payload["tags"][0]["created_at"]


def test_tree_cli_handles_an_empty_repository(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0

    assert invoke(["tree"], project, monkeypatch).stdout == "No commits yet\n"
    payload = json.loads(invoke(["tree", "--json"], project, monkeypatch).stdout)
    assert payload == {
        "commits": [],
        "branches": [
            {"name": "main", "commit_id": None, "comment": "", "current": True}
        ],
        "tags": [],
    }


def test_structured_json_output_for_major_commands(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "作品" / "絵.psd"
    asset.parent.mkdir()
    asset.write_bytes(b"image")
    stored_mtime_ns = asset.stat().st_mtime_ns
    assert invoke(["track", "作品/絵.psd"], project, monkeypatch).exit_code == 0

    status_result = invoke(
        ["status", "--tracked", "--untracked", "--json"], project, monkeypatch
    )
    assert status_result.exit_code == 0
    assert "作品/絵.psd" in status_result.stdout
    assert "\\u" not in status_result.stdout
    assert "On branch" not in status_result.stdout
    assert json.loads(status_result.stdout) == {
        "branch": "main",
        "changes": [{"state": "added", "path": "作品/絵.psd"}],
        "tracked": ["作品/絵.psd"],
        "untracked": [],
    }

    path_status = invoke(["status", "作品/絵.psd", "--json"], project, monkeypatch)
    assert path_status.exit_code == 0
    assert json.loads(path_status.stdout) == {
        "branch": "main",
        "paths": [{"path": "作品/絵.psd", "tracked": True}],
    }

    assert invoke(["commit", "-m", "日本語コミット"], project, monkeypatch).exit_code == 0
    commit_id = Repository.discover().log()[0]["id"]

    log_result = invoke(["log", "-n", "1", "--json"], project, monkeypatch)
    assert log_result.exit_code == 0
    log_payload = json.loads(log_result.stdout)
    assert log_payload == [
        {
            "id": commit_id,
            "parent_id": None,
            "created_at": log_payload[0]["created_at"],
            "message": "日本語コミット",
            "note": None,
            "note_updated_at": None,
            "labels": [],
        }
    ]
    assert "commit " not in log_result.stdout
    assert json.loads(invoke(["log", "missing.bin", "--json"], project, monkeypatch).stdout) == []

    show_result = invoke(["show", commit_id, "--json"], project, monkeypatch)
    assert show_result.exit_code == 0
    show_payload = json.loads(show_result.stdout)
    assert show_payload == {
        "id": commit_id,
        "parent_id": None,
        "branch_name": "main",
        "created_at": log_payload[0]["created_at"],
        "message": "日本語コミット",
        "note": None,
        "note_updated_at": None,
        "labels": [],
        "thumbnail": None,
        "files": [
            {
                "path": "作品/絵.psd",
                "object_hash": show_payload["files"][0]["object_hash"],
                "size": 5,
                "mtime_ns": stored_mtime_ns,
            }
        ],
    }
    assert "Date:" not in show_result.stdout

    assert invoke(["branch", "ideas", "-m", "案"], project, monkeypatch).exit_code == 0
    branch_result = invoke(["branch", "--json"], project, monkeypatch)
    assert branch_result.exit_code == 0
    assert json.loads(branch_result.stdout) == [
        {"name": "ideas", "commit_id": commit_id, "comment": "案", "current": False},
        {"name": "main", "commit_id": commit_id, "comment": "", "current": True},
    ]
    assert "* main" not in branch_result.stdout


def test_json_output_rejects_conflicting_display_or_mutation_options(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    assert invoke(["init", str(project)], tmp_path, monkeypatch).exit_code == 0
    asset = project / "asset.bin"
    asset.write_bytes(b"data")
    assert invoke(["track", "asset.bin"], project, monkeypatch).exit_code == 0
    assert invoke(["commit", "-m", "first"], project, monkeypatch).exit_code == 0
    commit_id = Repository.discover().log()[0]["id"]

    log_result = invoke(["log", "--json", "--oneline"], project, monkeypatch)
    assert log_result.exit_code != 0
    assert "--json and --oneline cannot be used together" in str(log_result.exception)

    show_result = invoke(
        ["show", commit_id, "--json", "--timezone", "Asia/Tokyo"], project, monkeypatch
    )
    assert show_result.exit_code != 0
    assert "--timezone cannot be used with --json" in str(show_result.exception)

    branch_result = invoke(["branch", "ideas", "--json"], project, monkeypatch)
    assert branch_result.exit_code != 0
    assert "--json can only be used when listing branches" in str(branch_result.exception)
