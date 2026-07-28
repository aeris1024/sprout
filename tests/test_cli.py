import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
    assert "Objects:       1 (4 bytes)" in result.stdout
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
