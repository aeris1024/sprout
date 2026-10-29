import os
import time
from contextlib import closing
from pathlib import Path

import pytest

from sprout.errors import SproutError
from sprout.repository import RACY_MARGIN_NS, Repository


def age(path, seconds=60):
    old = time.time_ns() - seconds * 1_000_000_000
    os.utime(path, ns=(old, old))


@pytest.fixture
def hashed(monkeypatch):
    """Record the names of files whose content is actually read for hashing."""
    calls: list[str] = []
    original = Repository.hash_file

    def counting(path, progress=None, label=None):
        calls.append(Path(path).name)
        return original(path, progress, label)

    monkeypatch.setattr(Repository, "hash_file", staticmethod(counting))
    return calls


def saved(tmp_path, count=3):
    repo = Repository.init(tmp_path / "project")
    files = []
    for index in range(count):
        path = repo.root / f"f{index}.bin"
        path.write_bytes(bytes([index]) * 100)
        age(path)
        files.append(path)
    repo.track(files)
    first = repo.commit("first").commit_id
    return repo, files, first


def fresh(repo):
    return Repository.discover(repo.root)


def test_unchanged_files_are_not_hashed_again(tmp_path, hashed):
    repo, files, _ = saved(tmp_path)
    assert fresh(repo).status() == []
    assert len(hashed) == 3
    hashed.clear()
    assert fresh(repo).status() == []
    assert fresh(repo).diff() == []
    assert hashed == []


def test_one_modified_file_is_the_only_one_hashed(tmp_path, hashed):
    repo, files, _ = saved(tmp_path)
    fresh(repo).status()
    hashed.clear()
    files[1].write_bytes(b"changed")
    assert [(e.state, e.path) for e in fresh(repo).status()] == [("modified", "f1.bin")]
    assert hashed == ["f1.bin"]


def test_same_size_rewrite_with_a_new_time_is_detected(tmp_path):
    repo, files, _ = saved(tmp_path)
    fresh(repo).status()
    files[0].write_bytes(b"\xff" * 100)
    age(files[0], seconds=30)
    assert [e.path for e in fresh(repo).status()] == ["f0.bin"]


def test_rewrite_inside_the_same_timestamp_granule_is_detected(tmp_path, hashed):
    # Simulate a coarse file system: the second write keeps the first write's time.
    repo, files, _ = saved(tmp_path)
    files[0].write_bytes(b"\x01" * 100)
    recent = files[0].stat().st_mtime_ns
    assert [e.path for e in fresh(repo).status()] == ["f0.bin"]
    files[0].write_bytes(b"\x00" * 100)
    os.utime(files[0], ns=(recent, recent))
    hashed.clear()
    assert fresh(repo).status() == []
    assert hashed == ["f0.bin"]


def test_racy_observation_is_trusted_once_it_is_old_enough(tmp_path, hashed):
    repo, files, _ = saved(tmp_path, count=1)
    files[0].write_bytes(b"\x02" * 100)
    fresh(repo).status()
    hashed.clear()
    fresh(repo).status()
    assert hashed == ["f0.bin"]
    with closing(repo.worktree_cache._connect()) as db, db:
        db.execute("UPDATE worktree_cache SET recorded_ns=recorded_ns+?", (RACY_MARGIN_NS,))
    hashed.clear()
    fresh(repo).status()
    assert hashed == []


def test_replaced_file_with_the_same_size_and_time_is_detected(tmp_path):
    repo, files, _ = saved(tmp_path)
    fresh(repo).status()
    replacement = repo.root / "replacement.tmp"
    replacement.write_bytes(b"\xee" * 100)
    info = files[2].stat()
    os.utime(replacement, ns=(info.st_atime_ns, info.st_mtime_ns))
    os.replace(replacement, files[2])
    assert [e.path for e in fresh(repo).status()] == ["f2.bin"]


@pytest.mark.parametrize("damage", ["bytes", "hash", "size", "missing"])
def test_damaged_or_mismatched_records_fall_back_to_hashing(tmp_path, hashed, damage):
    repo, files, _ = saved(tmp_path)
    fresh(repo).status()
    cache = repo.worktree_cache
    if damage == "bytes":
        cache.path.write_bytes(b"broken database")
    elif damage == "missing":
        cache.path.unlink()
    else:
        files[0].write_bytes(b"\x07" * (100 if damage == "hash" else 101))
        age(files[0])
    hashed.clear()
    status = fresh(repo).status()
    if damage in {"bytes", "missing"}:
        assert status == []
        assert sorted(hashed) == ["f0.bin", "f1.bin", "f2.bin"]
    else:
        assert [e.path for e in status] == ["f0.bin"]
        assert hashed == ["f0.bin"]


def test_file_changed_while_hashing_is_not_recorded(tmp_path, monkeypatch, hashed):
    repo, files, _ = saved(tmp_path, count=1)
    original = Repository.hash_file

    def racing(path, progress=None, label=None):
        result = original(path, progress, label)
        Path(path).write_bytes(b"\x09" * 100)
        age(path, seconds=10)
        return result

    monkeypatch.setattr(Repository, "hash_file", staticmethod(racing))
    fresh(repo).status()
    assert repo.worktree_cache.lookup(["f0.bin"]) == {}
    monkeypatch.undo()
    assert [e.path for e in fresh(repo).status()] == ["f0.bin"]


def test_unusable_cache_keeps_results_identical(tmp_path, monkeypatch):
    repo, files, first = saved(tmp_path)
    monkeypatch.setattr(repo.worktree_cache, "lookup", lambda paths: {})
    monkeypatch.setattr(repo.worktree_cache, "record", lambda entries: None)
    files[0].write_bytes(b"next")
    assert [e.path for e in repo.status()] == ["f0.bin"]
    repo.commit("second")
    assert repo.status() == []
    repo.restore(first)
    assert files[0].read_bytes() == bytes([0]) * 100


def test_moves_reuse_observations_and_keep_results(tmp_path, hashed):
    repo, files, first = saved(tmp_path)
    files[0].write_bytes(b"second")
    age(files[0])
    second = repo.commit("second").commit_id
    repo.create_branch("side", start_point=first)
    fresh(repo).status()

    hashed.clear()
    fresh(repo).restore(first)
    # Only the pre-move check that each file is unchanged reads content again.
    assert len(hashed) == 3
    assert files[0].read_bytes() == bytes([0]) * 100
    assert fresh(repo).status() == []

    fresh(repo).status()
    hashed.clear()
    result = fresh(repo).go(second)
    assert len(hashed) == 3
    assert result.bud is None
    assert files[0].read_bytes() == b"second"

    fresh(repo).status()
    files[1].write_bytes(b"unsaved")
    age(files[1])
    with pytest.raises(SproutError, match="uncommitted"):
        fresh(repo).switch("side")
    moved = fresh(repo).go(first)
    assert moved.bud is not None
    assert [c.path for c in moved.bud.changes] == ["f1.bin"]
    assert fresh(repo).status() == []

    files[2].write_bytes(b"committed")
    age(files[2])
    fresh(repo).status()
    third = fresh(repo).commit("third")
    assert fresh(repo).status() == []
    assert fresh(repo).manifest(third.commit_id)["f2.bin"].size == len(b"committed")
