import os
import sqlite3

import pytest
from PIL import Image

from sprout.cli import _tree_lines
from sprout.errors import SproutError
from sprout.repository import (
    SAVED_FILE_COMMITS_SQL,
    TIMESTAMP_PATTERN,
    Repository,
    utc_timestamp,
)


def committed_repo(tmp_path):
    repo = Repository.init(tmp_path / "project")
    asset = repo.root / "asset.bin"
    asset.write_bytes(b"base")
    repo.track([asset])
    commit = repo.commit("base").commit_id
    return repo, asset, commit


def test_branch_identity_survives_rename_and_name_reuse(tmp_path):
    repo, asset, first = committed_repo(tmp_path)
    original_id = repo.branch_id()
    asset.write_bytes(b"draft")
    bud = repo.save_bud()
    repo.restore(first, discard=True)
    repo.rename_branch("main", "renamed")
    repo.create_branch("main", start_point=first)
    assert repo.branch_id("main") != original_id
    assert repo.branch_id("renamed") == original_id
    repo.restore_bud(bud.id)
    assert repo.head_branch() == "renamed"
    assert asset.read_bytes() == b"draft"
    graph = repo.commit_graph()
    assert graph.commits[0].branch_id == original_id
    assert graph.commits[0].branch_name == "main"


def test_deleted_branch_bud_does_not_select_a_reused_name(tmp_path):
    repo, asset, first = committed_repo(tmp_path)
    repo.create_branch("side", switch=True)
    origin = repo.branch_id()
    asset.write_bytes(b"draft")
    bud = repo.save_bud()
    repo.switch("main", discard=True)
    repo.delete_branch("side")
    repo.create_branch("side", start_point=first)
    assert repo.branch_id("side") != origin
    repo.restore_bud(bud.id)
    assert repo.head_branch() == "main"
    with repo.connect() as db:
        assert tuple(db.execute("SELECT deleted, commit_id FROM branches WHERE id=?", (origin,)).fetchone()) == (1, None)


def test_deleted_branch_tip_is_not_protected_from_prune(tmp_path):
    repo, asset, _ = committed_repo(tmp_path)
    repo.create_branch("side", switch=True)
    origin = repo.branch_id()
    asset.write_bytes(b"side")
    tip = repo.commit("side").commit_id
    repo.switch("main")
    repo.delete_branch("side")
    assert tip in {c.id for c in repo.prune(all_history=True).commits}
    with repo.connect() as db:
        assert db.execute("SELECT deleted FROM branches WHERE id=?", (origin,)).fetchone()[0] == 1
    assert Repository.discover(repo.root).doctor().ok


def test_restore_precommit_bud_preserves_null_position_and_existing_tip(tmp_path):
    repo = Repository.init(tmp_path / "project")
    asset = repo.root / "asset.bin"
    asset.write_bytes(b"draft")
    repo.track([asset])
    assert repo.current_position() == (None, True)
    bud = repo.save_bud()
    asset.write_bytes(b"first")
    first = repo.commit("first").commit_id
    repo.restore_bud(bud.id)
    assert repo.current_position() == (None, False)
    reopened = Repository.discover(repo.root)
    with pytest.raises(SproutError, match="specify the start point"):
        reopened.create_branch("implicit")
    result = reopened.commit("new root")
    assert result.created_branch
    assert reopened.commit_info(result.commit_id)[0]["parent_id"] is None
    assert reopened.resolve_commit("main") == first


def test_multiple_attachments_keep_identity_order_and_gc_references(tmp_path):
    repo, _, commit = committed_repo(tmp_path)
    # Storage support only: public preview editing is implemented in TASK-38.
    source = repo.root / "preview.bin"
    source.write_bytes(b"only referenced by previews")
    digest, size = repo._store_object(source)
    now = utc_timestamp()
    with repo.connect() as db:
        repo._register_objects(db, {digest: size}, now)
        for attachment_id, position in [("later", 9), ("earlier", 2)]:
            db.execute(
                "INSERT INTO commit_attachments(id,commit_id,role,position,original_name,media_type,object_hash,size,created_at,updated_at) "
                "VALUES(?,?,'preview',?,'same.bin','application/x-future',?,?,?,?)",
                (attachment_id, commit, position, digest, size, now, now),
            )
    reopened = Repository.discover(repo.root)
    attachments = reopened.attachments_many([commit])[commit]
    assert [(a.id, a.position, a.original_name) for a in attachments] == [("earlier", 2, "same.bin"), ("later", 9, "same.bin")]
    assert reopened.commit_graph().commits[0].attachments == attachments
    assert digest not in reopened.gc(dry_run=True).objects
    assert reopened.doctor().ok


def test_thumbnail_replacement_preserves_id_and_singleton(tmp_path):
    repo, _, commit = committed_repo(tmp_path)
    source = repo.root / "thumbnail.png"
    Image.new("RGB", (2, 2), "red").save(source)
    first = repo.set_thumbnail(commit, source)
    Image.new("RGB", (3, 3), "blue").save(source)
    second = repo.set_thumbnail(commit, source)
    assert second.id == first.id
    assert second.object_hash != first.object_hash
    with repo.connect() as db, pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO commit_attachments(id,commit_id,role,position,original_name,media_type,object_hash,size,created_at,updated_at) SELECT 'duplicate', commit_id, role, position+1, original_name,media_type,object_hash,size,created_at,updated_at "
            "FROM commit_attachments WHERE id=?", (first.id,),
        )


@pytest.mark.parametrize("statement", [
    "UPDATE branches SET id=NULL",
    "UPDATE repository_state SET head_branch_id=NULL",
    "UPDATE repository_state SET current_commit_id='missing'",
    "UPDATE commits SET branch_id='missing'",
    "UPDATE commit_files SET size=-1",
    "UPDATE commit_files SET size='invalid'",
    "UPDATE commit_files SET size=1.5",
])
def test_database_rejects_invalid_identity_size_and_references(tmp_path, statement):
    repo, _, _ = committed_repo(tmp_path)
    with repo.connect() as db:
        db.execute("INSERT INTO file_identities(id) VALUES(?)", ('f' * 32,))
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute(statement)


@pytest.mark.parametrize("statement", [
    "DELETE FROM repository_state",
    "DROP TABLE repository_state",
    "DROP TABLE bud_files",
    "DROP INDEX idx_single_thumbnail",
    "ALTER TABLE commits DROP COLUMN message",
    "DROP TABLE objects",
    "DROP INDEX idx_commit_files_object",
])
def test_incomplete_v1_is_rejected_without_repair(tmp_path, statement):
    repo = Repository.init(tmp_path / "project")
    with repo.connect() as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute(statement)
    before = repo.db_path.read_bytes()
    with pytest.raises(SproutError, match="incomplete|invalid|unsupported"):
        Repository.discover(repo.root)
    assert repo.db_path.read_bytes() == before


@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt])
def test_failure_after_same_position_finalize_keeps_backup_bud(tmp_path, monkeypatch, failure):
    repo, asset, first = committed_repo(tmp_path)
    asset.write_bytes(b"valuable draft")
    finalize = repo._finalize_materialization

    def fail_after_finalize(*args, **kwargs):
        finalize(*args, **kwargs)
        raise failure("failure after durable commit")

    monkeypatch.setattr(repo, "_finalize_materialization", fail_after_finalize)
    with pytest.raises(failure):
        repo.go(first)
    assert asset.read_bytes() == b"base"
    assert len(repo.buds()) == 1
    assert repo.buds()[0].changes[0].path == "asset.bin"
    assert repo.gc(dry_run=True).removed_objects == 0


def cache_row(repo, relative):
    repo.worktree_cache.put(relative, size=1, mtime_ns=1, ctime_ns=1,
                            file_id="1", object_hash="0" * 64, recorded_ns=1)


def cached_paths(repo):
    # Read through the public cache API so expired history bindings are honored.
    return {p for p in ("asset.bin", "other.bin", "moved.bin") if repo.worktree_cache.get(p)}


def test_every_foreign_key_is_backed_by_an_index(tmp_path):
    repo = Repository.init(tmp_path / "project")
    with repo.connect() as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            if table == "repository_state":  # CHECK (id = 1) keeps it to one row.
                continue
            prefixes = set()
            for index in db.execute(f"PRAGMA index_list({table})"):
                columns = [row["name"] for row in db.execute(f"PRAGMA index_info({index['name']})")]
                prefixes.update(tuple(columns[:n]) for n in range(1, len(columns) + 1))
            keys: dict[int, list[str]] = {}
            for row in db.execute(f"PRAGMA foreign_key_list({table})"):
                keys.setdefault(row["id"], []).append(row["from"])
            for columns in keys.values():
                assert tuple(columns) in prefixes, (table, columns)


def test_saved_snapshot_lookup_uses_object_index(tmp_path):
    repo, _, _ = committed_repo(tmp_path)
    with repo.connect() as db:
        plan = " ".join(
            row["detail"]
            for row in db.execute("EXPLAIN QUERY PLAN " + SAVED_FILE_COMMITS_SQL, ("0" * 64, 1, "asset.bin"))
        )
    assert "idx_commit_files_object" in plan
    assert "SCAN commit_files" not in plan


def test_objects_record_storage_without_snapshot_file_times(tmp_path):
    repo, _, first = committed_repo(tmp_path)
    copy = repo.root / "copy.bin"
    copy.write_bytes(b"base")
    older = 1_600_000_000_123_456_789
    os.utime(copy, ns=(older, older))
    repo.track([copy])
    image = repo.root / "thumb.png"
    Image.new("RGB", (4, 4), "red").save(image)
    second = repo.commit("copy", thumbnail=image).commit_id
    with repo.connect() as db:
        rows = {row["hash"]: row for row in db.execute("SELECT * FROM objects")}
        columns = {row[1] for row in db.execute("PRAGMA table_info(commit_files)")}
    original = repo.manifest(first)["asset.bin"]
    thumbnail = repo.thumbnail(second)
    assert "mtime_ns" in columns
    assert set(rows) == {original.object_hash, thumbnail.object_hash}
    for object_hash, row in rows.items():
        stored = repo.objects / object_hash[:2] / object_hash
        assert (row["encoding"], row["stored_size"]) == ("zstd", stored.stat().st_size)
    assert "file_mtime_ns" not in rows[original.object_hash].keys()
    assert repo.manifest(second)["copy.bin"].mtime_ns == copy.stat().st_mtime_ns
    assert repo.manifest(first)["asset.bin"].mtime_ns == original.mtime_ns
    assert Repository.discover(repo.root).doctor().ok


def test_thumbnail_content_gets_file_time_when_first_committed_as_file(tmp_path):
    repo, _, first = committed_repo(tmp_path)
    image = repo.root / "art.png"
    Image.new("RGB", (4, 4), "blue").save(image)
    repo.set_thumbnail(first, image)
    file_time = 1_650_000_000_000_000_000
    os.utime(image, ns=(file_time, file_time))
    repo.track([image])
    second = repo.commit("art").commit_id
    assert repo.manifest(second)["art.png"].mtime_ns == file_time


@pytest.mark.parametrize("statement", [
    "INSERT INTO commit_files(commit_id, path, object_hash, size, mtime_ns, file_id) "
    "SELECT commit_id, 'other.bin', object_hash, size + 1, mtime_ns, 'ffffffffffffffffffffffffffffffff' FROM commit_files",
    "INSERT INTO commit_files(commit_id, path, object_hash, size, mtime_ns, file_id) "
    "SELECT commit_id, 'other.bin', 'f' || substr(object_hash, 2), size, mtime_ns, 'ffffffffffffffffffffffffffffffff' FROM commit_files",
    "DELETE FROM objects",
    "UPDATE objects SET hash='ABC'",
    "UPDATE objects SET stored_size=-1",
    "UPDATE commits SET created_at='2026-10-29T00:00:00+00:00'",
    "UPDATE commits SET seq=0",
])
def test_database_rejects_invalid_objects_times_order_and_cache(tmp_path, statement):
    repo, _, _ = committed_repo(tmp_path)
    with repo.connect() as db:
        db.execute("INSERT INTO file_identities(id) VALUES(?)", ('f' * 32,))
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute(statement)


def test_interrupted_object_registration_leaves_no_reference_and_gc_collects(tmp_path, monkeypatch):
    repo, asset, first = committed_repo(tmp_path)
    asset.write_bytes(b"never registered")
    register = repo._register_objects

    def fail_after_register(db, objects, created_at):
        register(db, objects, created_at)
        raise OSError("interrupted")

    monkeypatch.setattr(repo, "_register_objects", fail_after_register)
    with pytest.raises(OSError):
        repo.commit("lost")
    monkeypatch.undo()
    digest, _ = Repository.hash_file(asset)
    assert (repo.objects / digest[:2] / digest).is_file()
    assert [commit.id for commit in repo.commit_graph().commits] == [first]
    with repo.connect() as db:
        assert db.execute("SELECT 1 FROM objects WHERE hash=?", (digest,)).fetchone() is None
    assert {(issue.kind, issue.detail) for issue in repo.doctor().issues} == {("unregistered_object", digest)}
    assert repo.gc().objects == (digest,)
    assert repo.doctor().ok


def test_gc_forgets_unreferenced_objects_and_stats_follow_the_registry(tmp_path):
    repo, asset, first = committed_repo(tmp_path)
    asset.write_bytes(b"dropped draft")
    bud = repo.save_bud()
    draft = bud.files[0].object_hash
    repo.drop_bud(bud.id)
    assert repo.gc().objects == (draft,)
    kept = repo.manifest(first)["asset.bin"].object_hash
    with repo.connect() as db:
        assert {row[0] for row in db.execute("SELECT hash FROM objects")} == {kept}
    stats = repo.stats()
    assert (stats.objects, stats.objects_bytes) == (1, (repo.objects / kept[:2] / kept).stat().st_size)


@pytest.mark.parametrize(("statement", "kind"), [
    ("UPDATE objects SET stored_size=stored_size+1", "object_size_mismatch"),
    ("UPDATE objects SET encoding='future'", "unsupported_object_encoding"),
    ("DELETE FROM objects", "missing_object"),
])
def test_doctor_reports_object_registry_problems(tmp_path, statement, kind):
    repo, _, _ = committed_repo(tmp_path)
    with repo.connect() as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute(statement)
    assert kind in {issue.kind for issue in repo.doctor().issues}


def test_worktree_cache_is_cleared_by_untrack_move_restore_and_missing_files(tmp_path, monkeypatch):
    repo, asset, first = committed_repo(tmp_path)
    monkeypatch.chdir(repo.root)
    other = repo.root / "other.bin"
    other.write_bytes(b"other")
    repo.track([other])
    second = repo.commit("other").commit_id
    cache_row(repo, "asset.bin")
    cache_row(repo, "other.bin")

    repo.restore(first, [asset], discard=True)
    assert cached_paths(repo) == set()  # History writes conservatively expire all observations.
    repo.move(other, repo.root / "moved.bin")
    assert cached_paths(repo) == set()
    cache_row(repo, "moved.bin")
    repo.untrack([repo.root / "moved.bin"])
    assert cached_paths(repo) == set()

    repo.restore(second, discard=True)
    cache_row(repo, "asset.bin")
    repo.restore(first, discard=True)
    assert cached_paths(repo) == set()

    cache_row(repo, "asset.bin")
    asset.unlink()
    other.write_bytes(b"replacement")
    repo.track([other])
    repo.commit("asset removed")
    assert cached_paths(repo) == set()


def test_creation_sequence_orders_history_despite_clock_and_vacuum(tmp_path):
    repo, asset, first = committed_repo(tmp_path)
    asset.write_bytes(b"second")
    second = repo.commit("second").commit_id
    repo.restore(first, discard=True)
    asset.write_bytes(b"sibling")
    sibling = repo.commit("sibling").commit_id
    asset.write_bytes(b"draft one")
    one = repo.save_bud()
    asset.write_bytes(b"draft two")
    two = repo.save_bud()
    epoch = "2000-01-01T00:00:00.000000+00:00"
    with repo.connect() as db:
        # A clock moved backwards must not reorder history.
        db.execute("UPDATE commits SET created_at=? WHERE id=?", (epoch, sibling))
        db.execute("UPDATE buds SET created_at=? WHERE id=?", (epoch, two.id))
    db = sqlite3.connect(repo.db_path)
    try:
        db.execute("VACUUM")
    finally:
        db.close()
    reopened = Repository.discover(repo.root)
    graph = reopened.commit_graph()
    assert [commit.id for commit in graph.commits] == [sibling, second, first]
    assert [bud.id for bud in reopened.buds()] == [two.id, one.id]
    text = "\n".join(_tree_lines(graph))
    assert text.index(second[:12]) < text.index(sibling[:12])


def test_prune_lists_commits_in_creation_order(tmp_path):
    repo, asset, first = committed_repo(tmp_path)
    asset.write_bytes(b"second")
    second = repo.commit("second").commit_id
    asset.write_bytes(b"third")
    repo.commit("third")
    with repo.connect() as db:
        db.execute(
            "UPDATE commits SET created_at='2000-01-01T00:00:00.000000+00:00' WHERE id=?", (second,)
        )
    removed = [commit.id for commit in repo.prune(all_history=True, dry_run=True).commits]
    assert removed == [first, second]


def test_all_stored_times_share_utc_microsecond_format(tmp_path):
    repo, asset, first = committed_repo(tmp_path)
    image = repo.root / "thumb.png"
    Image.new("RGB", (4, 4), "green").save(image)
    repo.set_thumbnail(first, image)
    repo.set_note(first, "note")
    repo.create_tag("v1", first)
    asset.write_bytes(b"draft")
    repo.save_bud()
    with repo.connect() as db:
        values = [db.execute("SELECT value FROM meta WHERE key='repository_created_at'").fetchone()[0]]
        for table, column in [
            ("commits", "created_at"), ("objects", "created_at"), ("commit_attachments", "created_at"),
            ("commit_attachments", "updated_at"), ("commit_notes", "updated_at"),
            ("tags", "created_at"), ("buds", "created_at"),
        ]:
            values.extend(row[0] for row in db.execute(f"SELECT {column} FROM {table}"))
    assert len(values) == 10  # meta, commit, 3 objects, thumbnail x2, note, tag, bud
    assert all(TIMESTAMP_PATTERN.fullmatch(value) for value in values), values


def test_repository_created_at_must_use_the_stored_time_format(tmp_path):
    repo = Repository.init(tmp_path / "project")
    with repo.connect() as db:
        db.execute("UPDATE meta SET value='2026-10-29T00:00:00+00:00' WHERE key='repository_created_at'")
    with pytest.raises(SproutError, match="repository_created_at"):
        Repository.discover(repo.root)
