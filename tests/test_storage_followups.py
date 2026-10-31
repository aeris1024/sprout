import io
import json
import sqlite3
import sys
from contextlib import closing

import pytest
from PIL import Image

from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository, utc_timestamp


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


def unsupported(repo, digest):
    with repo.connect() as db:
        db.execute("UPDATE objects SET encoding='future' WHERE hash=?", (digest,))


@pytest.mark.parametrize("operation", ["restore", "partial", "go", "export", "cat", "commit", "bud", "register"])
def test_unsupported_encoding_rejects_without_changing_files_or_references(tmp_path, monkeypatch, operation):
    repo, asset, first = saved(tmp_path)
    monkeypatch.chdir(repo.root)
    digest = repo.manifest(first)["asset.bin"].object_hash
    unsupported(repo, digest)
    output = tmp_path / "output"
    output.mkdir()
    existing = output / "asset.bin"
    existing.write_bytes(b"valuable output")
    stream = io.BytesIO()
    if operation in {"restore", "partial", "go"}:
        asset.write_bytes(b"unsaved work")
    history = repo.db_path.read_bytes()
    original = asset.read_bytes()
    with pytest.raises(SproutError) as error:
        if operation == "restore":
            repo.restore(first, discard=True)
        elif operation == "partial":
            repo.restore(first, [asset], discard=True)
        elif operation == "go":
            repo.go(first)
        elif operation == "export":
            repo.export(first, output, force=True)
        elif operation == "cat":
            repo.cat(first, asset, stream)
        elif operation == "commit":
            repo.commit("reuse")
        elif operation == "bud":
            repo.save_bud()
        else:
            with repo.connect() as db:
                repo._register_objects(db, {digest: 4}, utc_timestamp())
    assert error.value.code == "unsupported_object_encoding"
    assert error.value.details == {"object_hash": digest, "encoding": "future"}
    assert digest in str(error.value) and "future" in str(error.value)
    assert repo.db_path.read_bytes() == history
    assert asset.read_bytes() == original
    assert existing.read_bytes() == b"valuable output"
    assert stream.getvalue() == b""
    assert not list(repo.tmp.glob("object-*"))
    assert "unsupported_object_encoding" in {issue.kind for issue in repo.doctor().issues}


def test_unsupported_thumbnail_read_and_reuse_are_nonmutating(tmp_path):
    repo, asset, first = saved(tmp_path)
    image = repo.root / "art.png"
    Image.new("RGB", (2, 2), "blue").save(image)
    repo.set_thumbnail(first, image)
    digest = repo.thumbnail(first).object_hash
    unsupported(repo, digest)
    destination = tmp_path / "thumbnail.png"
    destination.write_bytes(b"keep")
    before = repo.db_path.read_bytes()
    for operation in (lambda: repo.export_thumbnail(first, destination, force=True),
                      lambda: repo.set_thumbnail(first, image)):
        with pytest.raises(SproutError) as error:
            operation()
        assert error.value.code == "unsupported_object_encoding"
        assert error.value.details["object_hash"] == digest
        assert destination.read_bytes() == b"keep"
        assert repo.db_path.read_bytes() == before


def test_zstd_read_and_reuse_remain_supported(tmp_path):
    repo, asset, first = saved(tmp_path)
    stream = io.BytesIO()
    repo.cat(first, asset, stream)
    assert stream.getvalue() == b"base"
    other = repo.root / "copy.bin"
    other.write_bytes(b"base")
    repo.track([other])
    repo.commit("reuse")
    repo.restore(first, discard=True)
    assert asset.read_bytes() == b"base"
    assert repo.doctor().ok


@pytest.mark.parametrize("json_output", [False, True])
def test_unsupported_encoding_cli_error(tmp_path, monkeypatch, capsys, json_output):
    repo, asset, first = saved(tmp_path)
    digest = repo.manifest(first)["asset.bin"].object_hash
    unsupported(repo, digest)
    monkeypatch.chdir(repo.root)
    monkeypatch.setattr(sys, "argv", ["sprout", "go", first, "--keep-branch", "--discard"] + (["--json"] if json_output else []))
    assert cli.main() == 1
    captured = capsys.readouterr()
    if json_output:
        payload = json.loads(captured.err)
        assert payload["code"] == "unsupported_object_encoding"
        assert payload["details"] == {"object_hash": digest, "encoding": "future"}
    else:
        assert digest in captured.err and "future" in captured.err
