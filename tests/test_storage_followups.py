import sqlite3
from contextlib import closing

import pytest

from sprout.errors import SproutError
from sprout.repository import Repository


def saved(tmp_path):
    repo = Repository.init(tmp_path / "project")
    asset = repo.root / "asset.bin"
    asset.write_bytes(b"base")
    repo.track([asset])
    first = repo.commit("first").commit_id
    return repo, asset, first


def put(cache):
    cache.put("asset.bin", size=4, mtime_ns=1, ctime_ns=1, file_id="1",
              object_hash="0" * 64, recorded_ns=1)


@pytest.mark.parametrize("damage", ["missing", "bytes", "version", "table", "column", "directory"])
def test_cache_damage_never_changes_history_or_worktree(tmp_path, damage):
    repo, asset, first = saved(tmp_path)
    cache = repo.worktree_cache
    if damage == "bytes":
        cache.path.write_bytes(b"broken database")
    elif damage == "directory":
        cache.path.mkdir()
    elif damage != "missing":
        put(cache)
        with closing(sqlite3.connect(cache.path)) as db, db:
            db.execute({
                "version": "PRAGMA user_version=99",
                "table": "DROP TABLE worktree_cache",
                "column": "ALTER TABLE worktree_cache DROP COLUMN file_id",
            }[damage])
    history = repo.db_path.read_bytes()
    reopened = Repository.discover(repo.root)
    assert reopened.worktree_cache.get("asset.bin") is None
    assert reopened.current_commit() == first
    assert reopened.doctor().ok
    assert reopened.diff() == []
    assert repo.db_path.read_bytes() == history
    assert asset.read_bytes() == b"base"
    put(reopened.worktree_cache)
    assert bool(reopened.worktree_cache.get("asset.bin")) == (damage != "directory")
    asset.write_bytes(b"changed")
    assert reopened.diff()[0].path == "asset.bin"
    reopened.commit("second")
    reopened.restore(first, discard=True)
    assert asset.read_bytes() == b"base"


def test_cache_is_separate_and_expires_after_failed_invalidation(tmp_path, monkeypatch):
    repo, asset, first = saved(tmp_path)
    cache = repo.worktree_cache
    put(cache)
    assert cache.get("asset.bin")
    with repo.connect() as db:
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name='worktree_cache'").fetchone() is None
    monkeypatch.setattr(cache, "invalidate", lambda *args: None)
    repo.untrack([asset])
    reopened = Repository.discover(repo.root)
    assert reopened.worktree_cache.get("asset.bin") is None
    assert reopened.current_commit() == first


def test_legacy_cache_is_ignored_without_migration_or_history_repair(tmp_path):
    repo, asset, first = saved(tmp_path)
    with repo.connect() as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("CREATE TABLE worktree_cache(path TEXT REFERENCES tracked_paths(path))")
        db.execute("INSERT INTO worktree_cache VALUES('untracked.bin')")
    before = repo.db_path.read_bytes()
    reopened = Repository.discover(repo.root)
    assert reopened.current_commit() == first
    assert reopened.worktree_cache.get("untracked.bin") is None
    assert repo.db_path.read_bytes() == before
    assert asset.read_bytes() == b"base"


def test_unwritable_cache_falls_back_without_blocking_operations(tmp_path, monkeypatch):
    repo, asset, first = saved(tmp_path)
    cache = repo.worktree_cache
    put(cache)
    original_connect = sqlite3.connect

    def denied(database, *args, **kwargs):
        if str(database) == str(cache.path):
            raise sqlite3.OperationalError("readonly cache")
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", denied)
    assert cache.get("asset.bin") is None
    put(cache)
    cache.invalidate()
    assert Repository.discover(repo.root).current_commit() == first
    asset.write_bytes(b"next")
    repo.commit("next")
    repo.restore(first, discard=True)
    assert asset.read_bytes() == b"base"
    monkeypatch.undo()
    assert cache.get("asset.bin") is None


def test_locked_cache_is_not_replaced_and_history_is_readable(tmp_path):
    repo, asset, first = saved(tmp_path)
    cache = repo.worktree_cache
    put(cache)
    before = cache.path.read_bytes()
    with closing(sqlite3.connect(cache.path)) as blocker:
        blocker.execute("BEGIN EXCLUSIVE")
        assert cache.get("asset.bin") is None
        put(cache)
        cache.invalidate()
        assert Repository.discover(repo.root).current_commit() == first
        assert asset.read_bytes() == b"base"
        blocker.rollback()
    assert cache.path.read_bytes() == before
    assert cache.get("asset.bin")


def test_unsafe_cache_path_is_ignored(tmp_path, monkeypatch):
    repo, asset, first = saved(tmp_path)
    before = repo.db_path.read_bytes()

    def reject(path):
        raise SproutError("unsafe cache path")

    monkeypatch.setattr(repo.worktree_cache, "validate", reject)
    assert repo.worktree_cache.get("asset.bin") is None
    put(repo.worktree_cache)
    repo.worktree_cache.invalidate()
    assert not repo.worktree_cache.path.exists()
    assert repo.db_path.read_bytes() == before
    assert repo.current_commit() == first
    assert asset.read_bytes() == b"base"
