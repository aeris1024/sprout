import os
import json
import sqlite3
from pathlib import Path

import pytest

from sprout.errors import SproutError
from sprout.repository import Repository


def create_repo(tmp_path: Path) -> Repository:
    return Repository.init(tmp_path / "project")


def write(root: Path, relative: str, content: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_commit_multiple_files_restore_and_deduplicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    illustration = write(repo.root, "作品/絵.psd", b"pixels-v1")
    reference = write(repo.root, "refs/reference image.png", b"reference")
    first_mtime_ns = 1_700_000_000_123_456_700
    os.utime(illustration, ns=(first_mtime_ns, first_mtime_ns))
    repo.track([illustration, reference])

    first = repo.commit("first snapshot")
    illustration.write_bytes(b"pixels-v2")
    second_mtime_ns = 1_710_000_000_765_432_100
    os.utime(illustration, ns=(second_mtime_ns, second_mtime_ns))
    second = repo.commit("second snapshot")

    assert first != second
    assert len(list(repo.objects.glob("*/*"))) == 3
    repo.restore(first, discard=True)
    assert illustration.read_bytes() == b"pixels-v1"
    assert illustration.stat().st_mtime_ns == first_mtime_ns
    assert reference.read_bytes() == b"reference"
    assert {entry.path for entry in repo.status()} == {"作品/絵.psd"}

    repo.restore(second, discard=True)
    assert illustration.read_bytes() == b"pixels-v2"
    assert illustration.stat().st_mtime_ns == second_mtime_ns


def test_status_tracks_add_modify_delete_and_untrack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    first = write(repo.root, "first.bin", b"one")
    second = write(repo.root, "second.bin", b"two")
    repo.track([first])
    repo.commit("initial")

    first.write_bytes(b"changed")
    repo.track([second])
    assert [(e.state, e.path) for e in repo.status()] == [
        ("modified", "first.bin"),
        ("added", "second.bin"),
    ]

    first.unlink()
    assert ("deleted", "first.bin") in [(e.state, e.path) for e in repo.status()]
    repo.commit("replace first with second")
    assert repo.status() == []
    assert repo.tracked() == {"second.bin"}

    repo.untrack([second])
    assert [(e.state, e.path) for e in repo.status()] == [("deleted", "second.bin")]
    repo.commit("remove second")
    assert repo.status() == []


def test_branch_switch_and_dirty_protection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "model.blend", b"main-v1")
    repo.track([asset])
    main_commit = repo.commit("main")
    repo.create_branch("experiment", "Try a different shape")
    assert ("experiment", main_commit, "Try a different shape") in repo.branches()
    repo.set_branch_comment("experiment", "Try a different material")
    assert ("experiment", main_commit, "Try a different material") in repo.branches()
    repo.switch("experiment")
    asset.write_bytes(b"experiment")
    experiment_commit = repo.commit("experiment")

    asset.write_bytes(b"dirty")
    with pytest.raises(SproutError, match="uncommitted"):
        repo.switch("main")
    repo.switch("main", discard=True)
    assert repo.head_commit() == main_commit
    assert asset.read_bytes() == b"main-v1"

    repo.switch("experiment")
    assert repo.head_commit() == experiment_commit
    assert asset.read_bytes() == b"experiment"

    with pytest.raises(SproutError, match="unknown branch"):
        repo.set_branch_comment("missing", "nope")


def test_discard_refuses_to_delete_never_committed_tracked_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"main")
    repo.track([asset])
    main_commit = repo.commit("main")
    repo.create_branch("experiment")
    added = write(repo.root, "new.bin", b"only copy")
    repo.track([added])

    with pytest.raises(SproutError, match="never been committed"):
        repo.switch("experiment", discard=True)

    assert repo.head_branch() == "main"
    assert repo.head_commit() == main_commit
    assert added.read_bytes() == b"only copy"
    assert "new.bin" in repo.tracked()

    with pytest.raises(SproutError, match="never been committed"):
        repo.restore(main_commit, discard=True)
    assert added.read_bytes() == b"only copy"


def test_untracked_file_is_never_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "shared.dat", b"tracked")
    repo.track([asset])
    repo.commit("with file")
    repo.create_branch("with-file")
    repo.untrack([asset])
    repo.commit("without file")
    asset.write_bytes(b"untracked")

    with pytest.raises(SproutError, match="untracked path"):
        repo.switch("with-file", discard=True)
    assert asset.read_bytes() == b"untracked"


def test_rejects_outside_paths_and_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    outside = write(tmp_path, "outside.txt", b"no")
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    write(outside_dir, "child.txt", b"no")
    with pytest.raises(SproutError, match="outside"):
        repo.track([outside])
    with pytest.raises(SproutError, match="outside"):
        repo.track([outside_dir])
    with pytest.raises(SproutError, match="metadata"):
        repo.track([repo.db_path])


def test_tracking_directory_does_not_follow_nested_symlink_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    assets = repo.root / "assets"
    assets.mkdir()
    write(repo.root, "assets/local.txt", b"local")
    outside = tmp_path / "outside"
    outside.mkdir()
    write(outside, "secret.txt", b"outside")
    try:
        os.symlink(outside, assets / "linked")
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks are not available: {exc}")

    assert repo.track([assets]) == ["assets/local.txt"]


def test_detects_corrupt_object_before_restore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"valid")
    repo.track([asset])
    commit_id = repo.commit("valid")
    state = repo.manifest(commit_id)["asset.bin"]
    object_path = repo.objects / state.object_hash[:2] / state.object_hash
    object_path.write_bytes(b"corrupt")
    asset.write_bytes(b"dirty")

    with pytest.raises(SproutError, match="corrupt object"):
        repo.restore(commit_id, discard=True)
    assert asset.read_bytes() == b"dirty"


def test_tracking_status_for_files_and_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    tracked = write(repo.root, "assets/model.blend", b"model")
    untracked = write(repo.root, "assets/notes.txt", b"notes")
    empty_dir = repo.root / "empty"
    empty_dir.mkdir()
    repo.track([tracked])

    assert repo.tracking_status([tracked, untracked]) == [
        ("assets/model.blend", True),
        ("assets/notes.txt", False),
    ]
    assert repo.tracking_status([repo.root / "assets"]) == [("assets/model.blend", True)]
    assert repo.tracking_status([empty_dir]) == [("empty/", False)]
    assert repo.untracked_files() == ["assets/notes.txt"]

    metadata_file = write(repo.control, "tmp/internal", b"ignore")
    assert metadata_file.is_file()
    assert repo.untracked_files() == ["assets/notes.txt"]


def test_timestamp_only_change_is_not_committable_and_restores_first_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "same.png", b"identical-content")
    old_time = 1_700_000_000_000_000_000
    new_time = 1_720_000_000_000_000_000
    os.utime(asset, ns=(old_time, old_time))
    repo.track([asset])
    old_commit = repo.commit("old timestamp")

    os.utime(asset, ns=(new_time, new_time))
    assert repo.status() == []
    with pytest.raises(SproutError, match="nothing to commit"):
        repo.commit("new timestamp")
    assert len(list(repo.objects.glob("*/*"))) == 1

    repo.restore(old_commit, discard=True)
    assert asset.stat().st_mtime_ns == old_time


def test_duplicate_content_uses_oldest_time_on_first_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    older = write(repo.root, "z-older.png", b"same")
    newer = write(repo.root, "a-newer.png", b"same")
    old_time = 1_700_000_000_000_000_000
    new_time = 1_720_000_000_000_000_000
    os.utime(older, ns=(old_time, old_time))
    os.utime(newer, ns=(new_time, new_time))
    repo.track([older, newer])
    commit_id = repo.commit("duplicates")

    manifest = repo.manifest(commit_id)
    assert manifest["z-older.png"].mtime_ns == old_time
    assert manifest["a-newer.png"].mtime_ns == old_time
    assert len(list(repo.objects.glob("*/*"))) == 1

    os.utime(older, ns=(new_time, new_time))
    os.utime(newer, ns=(new_time, new_time))
    repo.restore(commit_id, discard=True)
    assert older.stat().st_mtime_ns == old_time
    assert newer.stat().st_mtime_ns == old_time


def repository_with_divergent_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Repository, Path, Path]:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    base = write(repo.root, "base.bin", b"main")
    repo.track([base])
    repo.commit("main")
    repo.create_branch("other")
    repo.switch("other")
    base.write_bytes(b"other")
    added = write(repo.root, "added.bin", b"added")
    repo.track([added])
    repo.commit("other")
    repo.switch("main")
    return repo, base, added


def test_restore_rolls_back_when_timestamp_update_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base, added = repository_with_divergent_branch(tmp_path, monkeypatch)
    real_utime = os.utime

    def fail_for_added(path, *args, **kwargs):
        if Path(path).name == "added.bin":
            raise OSError("simulated timestamp failure")
        return real_utime(path, *args, **kwargs)

    monkeypatch.setattr(os, "utime", fail_for_added)
    with pytest.raises(OSError, match="timestamp failure"):
        repo.switch("other")

    assert repo.head_branch() == "main"
    assert repo.tracked() == {"base.bin"}
    assert base.read_bytes() == b"main"
    assert not added.exists()


def test_restore_rolls_back_when_database_update_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, base, added = repository_with_divergent_branch(tmp_path, monkeypatch)

    def fail_finalize(*args, **kwargs):
        raise sqlite3.OperationalError("simulated database failure")

    monkeypatch.setattr(repo, "_finalize_materialization", fail_finalize)
    with pytest.raises(sqlite3.OperationalError, match="database failure"):
        repo.switch("other")

    assert repo.head_branch() == "main"
    assert repo.tracked() == {"base.bin"}
    assert base.read_bytes() == b"main"
    assert not added.exists()


def test_discovers_and_recovers_interrupted_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"original")
    repo.track([asset])
    repo.commit("initial")

    operation_id = "restore-interrupted"
    operation_dir = repo.tmp / operation_id
    backup = operation_dir / "backup"
    backup.mkdir(parents=True)
    os.replace(asset, backup / "asset.bin")
    asset.write_bytes(b"partial replacement")
    (operation_dir / "plan.json").write_text(json.dumps({"new_paths": []}), encoding="utf-8")
    repo._set_active_operation(operation_id)

    recovered = Repository.discover(repo.root)
    assert asset.read_bytes() == b"original"
    assert not operation_dir.exists()
    with recovered.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()[0] == ""


def test_mutations_are_rejected_while_repository_is_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"data")

    with repo.lock():
        with pytest.raises(SproutError, match="already running"):
            repo.track([asset])


def test_rejects_empty_commit_ref_and_hex_branch_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"data")
    repo.track([asset])
    repo.commit("initial")

    with pytest.raises(SproutError, match="commit id required"):
        repo.resolve_commit("")
    with pytest.raises(SproutError, match="commit id required"):
        repo.resolve_commit("   ")
    with pytest.raises(SproutError, match="commit id prefix"):
        repo.create_branch("1234abcd")
    repo.create_branch("idea-1234")


def test_rejects_branch_before_first_commit(tmp_path: Path) -> None:
    repo = create_repo(tmp_path)

    with pytest.raises(SproutError, match="before first commit"):
        repo.create_branch("experiment")


def test_connect_closes_database_connection(tmp_path: Path) -> None:
    repo = create_repo(tmp_path)

    with repo.connect() as db:
        db.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        db.execute("SELECT 1")
