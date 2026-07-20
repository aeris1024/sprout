import os
import json
import sqlite3
from contextlib import contextmanager
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

    repo.restore(second)
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


def test_diff_classifies_added_modified_deleted_between_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    first = write(repo.root, "keep.bin", b"same")
    second = write(repo.root, "old.bin", b"remove-me")
    repo.track([first, second])
    older = repo.commit("older")

    second.unlink()
    repo.untrack([second])
    first.write_bytes(b"changed")
    added = write(repo.root, "new.bin", b"brand-new")
    repo.track([first, added])
    newer = repo.commit("newer")

    entries = repo.diff(older, newer)
    assert [(entry.state, entry.path) for entry in entries] == [
        ("modified", "keep.bin"),
        ("added", "new.bin"),
        ("deleted", "old.bin"),
    ]
    modified = entries[0]
    assert modified.old_size == len(b"same")
    assert modified.new_size == len(b"changed")


def test_diff_against_working_tree_and_commit_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    first = repo.commit("first")
    repo.create_branch("other")
    asset.write_bytes(b"v2")
    second = repo.commit("second")

    asset.write_bytes(b"working")
    working = repo.diff()
    assert [(entry.state, entry.path, entry.old_size, entry.new_size) for entry in working] == [
        ("modified", "asset.bin", len(b"v2"), len(b"working")),
    ]

    against_first = repo.diff(first[:12])
    assert [(entry.state, entry.path) for entry in against_first] == [("modified", "asset.bin")]

    between_branches = repo.diff("other", "main")
    assert [(entry.state, entry.path) for entry in between_branches] == [("modified", "asset.bin")]
    between_commits = repo.diff(first, second)
    assert [(entry.state, entry.path) for entry in between_commits] == [("modified", "asset.bin")]
    assert repo.diff("main", second) == []


def test_sproutignore_skips_files_for_directory_track_and_untracked_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    (repo.root / ".sproutignore").write_text(
        "# temporary files\n*.tmp\nThumbs.db\ncache/\n",
        encoding="utf-8",
    )
    write(repo.root, "work/keep.bin", b"keep")
    write(repo.root, "work/noise.tmp", b"tmp")
    write(repo.root, "work/Thumbs.db", b"thumbs")
    write(repo.root, "work/cache/nested.bin", b"cache")
    write(repo.root, "work/docs/note.bin", b"note")

    assert repo.untracked_files() == [
        ".sproutignore",
        "work/docs/note.bin",
        "work/keep.bin",
    ]

    tracked = repo.track([Path("work")])
    assert tracked == ["work/docs/note.bin", "work/keep.bin"]
    assert "work/noise.tmp" not in tracked
    assert "work/Thumbs.db" not in tracked
    assert "work/cache/nested.bin" not in tracked
    assert repo.untracked_files() == [".sproutignore"]


def test_sproutignore_explicit_track_overrides_patterns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    (repo.root / ".sproutignore").write_text("*.tmp\n", encoding="utf-8")
    ignored = write(repo.root, "work/draft.tmp", b"draft")
    write(repo.root, "work/ok.bin", b"ok")

    assert repo.track([Path("work")]) == ["work/ok.bin"]
    assert repo.track([ignored]) == ["work/draft.tmp"]
    assert "work/draft.tmp" in repo.tracked()


def test_sproutignore_does_not_affect_tracked_status_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.tmp", b"v1")
    repo.track([asset])
    repo.commit("initial")
    (repo.root / ".sproutignore").write_text("*.tmp\n", encoding="utf-8")
    asset.write_bytes(b"v2")

    assert [(entry.state, entry.path) for entry in repo.status()] == [("modified", "asset.tmp")]
    assert "asset.tmp" not in repo.untracked_files()


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


def test_switch_allows_saved_snapshot_without_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"main")
    repo.track([asset])
    main_commit = repo.commit("main")
    repo.create_branch("other")
    repo.switch("other")
    asset.write_bytes(b"other")
    other_commit = repo.commit("other")
    repo.restore(main_commit, discard=True)

    repo.switch("other")

    assert repo.head_commit() == other_commit
    assert asset.read_bytes() == b"other"
    assert repo.status() == []


def test_switch_rejects_unsaved_changes_without_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"main")
    repo.track([asset])
    repo.commit("main")
    repo.create_branch("other")
    repo.switch("other")
    asset.write_bytes(b"other")
    repo.commit("other")
    asset.write_bytes(b"unsaved")

    with pytest.raises(SproutError, match="uncommitted"):
        repo.switch("main")


def test_has_unsaved_changes_hashes_each_tracked_file_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    first = write(repo.root, "first.bin", b"one")
    second = write(repo.root, "second.bin", b"two")
    repo.track([first, second])
    repo.commit("initial")
    first.write_bytes(b"changed")

    calls: list[str] = []
    original = Repository.hash_file

    @staticmethod
    def counting_hash(path: Path) -> tuple[str, int]:
        calls.append(path.relative_to(repo.root).as_posix())
        return original(path)

    monkeypatch.setattr(Repository, "hash_file", counting_hash)
    assert repo._has_unsaved_changes() is True
    assert sorted(calls) == ["first.bin", "second.bin"]
    assert len(calls) == 2


def test_is_saved_snapshot_does_not_load_all_commit_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    repo.commit("first")
    asset.write_bytes(b"v2")
    repo.commit("second")
    asset.write_bytes(b"v1")
    signature = {
        "asset.bin": Repository.hash_file(asset),
    }

    queries: list[str] = []
    original_connect = repo.connect

    @contextmanager
    def guarded_connect():
        with original_connect() as db:

            class GuardedConnection:
                def execute(self, sql: str, parameters=()):
                    queries.append(" ".join(sql.split()))
                    return db.execute(sql, parameters)

                def __getattr__(self, name: str):
                    return getattr(db, name)

            yield GuardedConnection()

    monkeypatch.setattr(repo, "connect", guarded_connect)
    assert repo._is_saved_snapshot(signature) is True
    assert any("GROUP BY commit_id" in sql and "HAVING COUNT(*)" in sql for sql in queries)
    assert any("WHERE commit_id=?" in sql for sql in queries)
    assert not any(
        "FROM commit_files" in sql
        and "WHERE" not in sql
        and "GROUP BY" not in sql
        for sql in queries
    )


def test_discard_removes_never_committed_tracked_files(
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

    with pytest.raises(SproutError, match="uncommitted"):
        repo.switch("experiment")
    repo.switch("experiment", discard=True)
    assert not added.exists()
    assert repo.tracked() == {"asset.bin"}

    added = write(repo.root, "new.bin", b"second only copy")
    repo.track([added])
    with pytest.raises(SproutError, match="uncommitted"):
        repo.restore(main_commit)
    repo.restore(main_commit, discard=True)
    assert not added.exists()
    assert repo.tracked() == {"asset.bin"}


def test_discard_restores_uncommitted_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    original = write(repo.root, "original.bin", b"content")
    repo.track([original])
    main_commit = repo.commit("main")
    repo.create_branch("experiment")
    moved = repo.root / "nested/moved.bin"

    repo.move(original, Path("nested/moved.bin"))
    with pytest.raises(SproutError, match="uncommitted"):
        repo.switch("experiment")
    repo.switch("experiment", discard=True)
    assert original.read_bytes() == b"content"
    assert not moved.exists()

    repo.move(original, Path("nested/moved.bin"))
    with pytest.raises(SproutError, match="uncommitted"):
        repo.restore(main_commit)
    repo.restore(main_commit, discard=True)
    assert original.read_bytes() == b"content"
    assert not moved.exists()


def test_restore_moves_between_saved_commits_without_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    first = repo.commit("v1")
    asset.write_bytes(b"v2")
    second = repo.commit("v2")

    repo.restore(first, discard=True)
    assert asset.read_bytes() == b"v1"
    repo.restore("main")

    assert repo.head_commit() == second
    assert asset.read_bytes() == b"v2"
    assert repo.status() == []


def test_restore_can_return_to_tip_that_deleted_restored_file_without_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"saved")
    repo.track([asset])
    old_commit = repo.commit("add asset")
    asset.unlink()
    latest_commit = repo.commit("remove asset")

    repo.restore(old_commit, discard=True)
    assert asset.read_bytes() == b"saved"
    repo.restore("main")

    assert repo.head_commit() == latest_commit
    assert not asset.exists()
    assert repo.status() == []


def test_restore_can_leave_deleted_snapshot_without_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    repo.commit("add asset")
    asset.unlink()
    deleted_commit = repo.commit("remove asset")
    asset.write_bytes(b"v2")
    repo.track([asset])
    latest_commit = repo.commit("add asset again")

    repo.restore(deleted_commit, discard=True)
    assert not asset.exists()
    repo.restore("main")

    assert repo.head_commit() == latest_commit
    assert asset.read_bytes() == b"v2"
    assert repo.status() == []


def test_partial_restore_updates_only_selected_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    first = write(repo.root, "keep.bin", b"keep-v1")
    second = write(repo.root, "docs/manual.bin", b"manual-v1")
    repo.track([first, second])
    old = repo.commit("old")
    first.write_bytes(b"keep-v2")
    second.write_bytes(b"manual-v2")
    repo.commit("new")
    head_before = repo.head_commit()
    tracked_before = repo.tracked()

    first.write_bytes(b"keep-unsaved")
    repo.restore(old, [Path("docs/manual.bin")])

    assert second.read_bytes() == b"manual-v1"
    assert first.read_bytes() == b"keep-unsaved"
    assert repo.head_commit() == head_before
    assert repo.head_branch() == "main"
    assert repo.tracked() == tracked_before


def test_partial_restore_expands_directory_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    nested = write(repo.root, "assets/a.bin", b"a1")
    other = write(repo.root, "assets/b.bin", b"b1")
    outside = write(repo.root, "root.bin", b"root1")
    repo.track([nested, other, outside])
    old = repo.commit("old")
    nested.write_bytes(b"a2")
    other.write_bytes(b"b2")
    outside.write_bytes(b"root2")
    repo.commit("new")

    repo.restore(old, [Path("assets")])

    assert nested.read_bytes() == b"a1"
    assert other.read_bytes() == b"b1"
    assert outside.read_bytes() == b"root2"


def test_partial_restore_rejects_missing_commit_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"data")
    repo.track([asset])
    commit_id = repo.commit("initial")

    with pytest.raises(SproutError, match="path not in commit"):
        repo.restore(commit_id, [Path("missing.bin")])


def test_partial_restore_requires_discard_only_for_selected_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    first = write(repo.root, "first.bin", b"v1")
    second = write(repo.root, "second.bin", b"v1")
    repo.track([first, second])
    old = repo.commit("old")
    first.write_bytes(b"v2")
    second.write_bytes(b"v2")
    repo.commit("new")
    first.write_bytes(b"unsaved-first")
    second.write_bytes(b"unsaved-second")

    with pytest.raises(SproutError, match="uncommitted"):
        repo.restore(old, [Path("first.bin")])
    repo.restore(old, [Path("first.bin")], discard=True)

    assert first.read_bytes() == b"v1"
    assert second.read_bytes() == b"unsaved-second"


def test_partial_restore_rejects_untracked_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"tracked")
    repo.track([asset])
    old = repo.commit("with asset")
    asset.unlink()
    repo.untrack([asset])
    repo.commit("remove asset")
    write(repo.root, "asset.bin", b"untracked")

    with pytest.raises(SproutError, match="untracked path would be overwritten"):
        repo.restore(old, [Path("asset.bin")])


def test_manual_delete_still_requires_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    repo.commit("add asset")
    asset.unlink()
    repo.commit("remove asset")
    asset.write_bytes(b"v2")
    repo.track([asset])
    repo.commit("add asset again")

    asset.unlink()

    with pytest.raises(SproutError, match="uncommitted"):
        repo.restore("main")


def test_restore_refuses_to_delete_edited_restored_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"saved")
    repo.track([asset])
    old_commit = repo.commit("add asset")
    asset.unlink()
    repo.commit("remove asset")

    repo.restore(old_commit, discard=True)
    asset.write_bytes(b"edited after restore")

    with pytest.raises(SproutError, match="uncommitted"):
        repo.restore("main")
    repo.restore("main", discard=True)
    assert not asset.exists()


def test_restore_can_discard_saved_file_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"v1")
    repo.track([asset])
    repo.commit("v1")
    asset.write_bytes(b"v2")
    repo.commit("v2")

    asset.write_bytes(b"unsaved edit")
    with pytest.raises(SproutError, match="uncommitted"):
        repo.restore("main")

    repo.restore("main", discard=True)
    assert asset.read_bytes() == b"v2"
    assert repo.status() == []


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

    for discard in (False, True):
        with pytest.raises(SproutError, match="untracked path"):
            repo.switch("with-file", discard=discard)
        assert asset.read_bytes() == b"untracked"


def test_switch_removes_empty_directories_but_keeps_nonempty_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    removed = write(repo.root, "gone/nested/tracked.bin", b"gone")
    kept = write(repo.root, "kept/nested/tracked.bin", b"kept")
    repo.track([removed, kept])
    repo.commit("with nested files")
    repo.create_branch("with-files")
    removed.unlink()
    kept.unlink()
    repo.commit("without nested files")

    repo.switch("with-files")
    untracked = write(repo.root, "kept/nested/notes.txt", b"keep directory")
    repo.switch("main")

    assert not (repo.root / "gone").exists()
    assert untracked.read_bytes() == b"keep directory"
    assert (repo.root / "kept/nested").is_dir()
    assert repo.root.is_dir()
    assert repo.control.is_dir()


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


def test_move_tracked_file_updates_file_and_tracking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    source = write(repo.root, "old.txt", b"content")
    repo.track([source])
    first = repo.commit("add file")

    assert repo.move(source, Path("dir/new.txt")) == ("old.txt", "dir/new.txt")
    assert not source.exists()
    moved = repo.root / "dir/new.txt"
    assert moved.read_bytes() == b"content"
    assert repo.tracked() == {"dir/new.txt"}
    assert {(entry.state, entry.path) for entry in repo.status()} == {
        ("deleted", "old.txt"),
        ("added", "dir/new.txt"),
    }

    second = repo.commit("move file")
    assert repo.status() == []
    repo.restore(first, discard=True)
    assert source.read_bytes() == b"content"
    assert not moved.exists()
    repo.restore(second, discard=True)
    assert moved.read_bytes() == b"content"
    assert not source.exists()


def test_move_rejects_invalid_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    tracked = write(repo.root, "tracked.txt", b"tracked")
    untracked = write(repo.root, "untracked.txt", b"untracked")
    existing = write(repo.root, "existing.txt", b"existing")
    directory = repo.root / "dir"
    directory.mkdir()
    repo.track([tracked])

    with pytest.raises(SproutError, match="not tracked"):
        repo.move(untracked, Path("new.txt"))
    with pytest.raises(SproutError, match="does not exist"):
        repo.move(Path("missing.txt"), Path("new.txt"))
    with repo.connect() as db:
        db.execute("INSERT INTO tracked_paths(path) VALUES('dir')")
    with pytest.raises(SproutError, match="not a file"):
        repo.move(directory, Path("new.txt"))
    with pytest.raises(SproutError, match="destination already exists"):
        repo.move(tracked, existing)
    with repo.connect() as db:
        db.execute("INSERT INTO tracked_paths(path) VALUES('reserved.txt')")
    with pytest.raises(SproutError, match="already tracked"):
        repo.move(tracked, Path("reserved.txt"))
    with pytest.raises(SproutError, match="outside"):
        repo.move(tracked, tmp_path / "outside.txt")
    with pytest.raises(SproutError, match="metadata"):
        repo.move(tracked, repo.control / "moved.txt")


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


def test_discover_skips_lock_when_no_active_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)

    def refuse_lock(self: Repository):
        raise AssertionError("lock should not be acquired when active_operation is empty")

    monkeypatch.setattr(Repository, "lock", refuse_lock)
    discovered = Repository.discover(repo.root)
    assert discovered.root == repo.root


def test_status_and_log_succeed_while_repository_is_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"data")
    repo.track([asset])
    commit_id = repo.commit("initial")

    with repo.lock():
        discovered = Repository.discover(repo.root)
        assert discovered.status() == []
        rows = discovered.log()
        assert len(rows) == 1
        assert rows[0]["id"] == commit_id


def test_discover_recovers_only_when_active_operation_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    lock_calls: list[str] = []
    original_lock = Repository.lock

    @contextmanager
    def tracking_lock(self: Repository):
        lock_calls.append("lock")
        with original_lock(self):
            yield

    monkeypatch.setattr(Repository, "lock", tracking_lock)

    Repository.discover(repo.root)
    assert lock_calls == []

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

    lock_calls.clear()
    recovered = Repository.discover(repo.root)
    assert lock_calls == ["lock"]
    assert asset.read_bytes() == b"original"
    assert not operation_dir.exists()
    with recovered.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()[0] == ""


def test_gc_removes_orphans_and_keeps_referenced_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"kept-content")
    repo.track([asset])
    repo.commit("initial")
    kept = next(repo.objects.glob("*/*"))

    orphan_hash = "ab" + ("0" * 62)
    orphan = repo.objects / orphan_hash[:2] / orphan_hash
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"orphan-bytes")
    stale_temp = repo.tmp / "object-stale"
    stale_temp.write_bytes(b"temp-bytes")

    result = repo.gc()
    assert result.removed_objects == 1
    assert result.removed_temps == 1
    assert result.freed_bytes == len(b"orphan-bytes") + len(b"temp-bytes")
    assert result.objects == (orphan_hash,)
    assert result.temps == ("object-stale",)
    assert kept.is_file()
    assert not orphan.exists()
    assert not stale_temp.exists()
    assert not (repo.objects / orphan_hash[:2]).exists()


def test_gc_dry_run_lists_targets_without_deleting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    orphan_hash = "cd" + ("1" * 62)
    orphan = repo.objects / orphan_hash[:2] / orphan_hash
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"orphan")
    stale_temp = repo.tmp / "object-dry"
    stale_temp.write_bytes(b"tmp")

    result = repo.gc(dry_run=True)
    assert result.dry_run is True
    assert result.removed_objects == 1
    assert result.removed_temps == 1
    assert orphan.is_file()
    assert stale_temp.is_file()


def test_gc_is_rejected_while_repository_is_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    with repo.lock():
        with pytest.raises(SproutError, match="already running"):
            repo.gc()


def test_rejects_empty_commit_ref_and_hex_branch_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    asset = write(repo.root, "asset.bin", b"data")
    repo.track([asset])
    commit_id = repo.commit("initial")

    with pytest.raises(SproutError, match="commit id required"):
        repo.resolve_commit("")
    with pytest.raises(SproutError, match="commit id required"):
        repo.resolve_commit("   ")
    with pytest.raises(SproutError, match="commit id prefix"):
        repo.create_branch("1234abcd")
    repo.create_branch("idea-1234")
    assert repo.resolve_commit(commit_id) == commit_id
    assert repo.resolve_commit(commit_id[:12]) == commit_id
    assert repo.resolve_commit("main") == commit_id
    for value in ("%", "_", commit_id[:4] + "%", commit_id[:4] + "_"):
        with pytest.raises(SproutError, match="unknown commit"):
            repo.resolve_commit(value)


@pytest.mark.skipif(os.name != "nt", reason="Windows path matching is case-insensitive")
def test_untrack_deleted_file_ignores_case_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    tracked = write(repo.root, "folder/file.txt", b"data")
    repo.track([tracked])
    tracked.unlink()

    assert repo.untrack([Path("FOLDER/FILE.TXT")]) == ["folder/file.txt"]
    assert repo.tracked() == set()


@pytest.mark.skipif(os.name == "nt", reason="Case-sensitive behavior is for non-Windows systems")
def test_untrack_deleted_file_preserves_case_sensitivity_off_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = create_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    tracked = write(repo.root, "folder/file.txt", b"data")
    repo.track([tracked])
    tracked.unlink()

    assert repo.untrack([Path("FOLDER/FILE.TXT")]) == []
    assert repo.tracked() == {"folder/file.txt"}


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
