import sqlite3

import pytest
from PIL import Image

from sprout.errors import SproutError
from sprout.repository import Repository


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
    with repo.connect() as db:
        for attachment_id, position in [("later", 9), ("earlier", 2)]:
            db.execute(
                "INSERT INTO commit_attachments(id,commit_id,role,position,original_name,media_type,object_hash,size,created_at,updated_at) "
                "VALUES(?,?,'preview',?,'same.bin','application/x-future',?,?,'now','now')",
                (attachment_id, commit, position, digest, size),
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
            "INSERT INTO commit_attachments SELECT 'duplicate', commit_id, role, position+1, original_name,media_type,object_hash,size,created_at,updated_at "
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
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute(statement)


@pytest.mark.parametrize("statement", [
    "DELETE FROM repository_state",
    "DROP TABLE repository_state",
    "DROP TABLE bud_files",
    "DROP INDEX idx_single_thumbnail",
    "ALTER TABLE commits DROP COLUMN branch_id",
])
def test_incomplete_v1_is_rejected_without_repair(tmp_path, statement):
    repo = Repository.init(tmp_path / "project")
    with repo.connect() as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute(statement)
    before = repo.db_path.read_bytes()
    with pytest.raises(SproutError, match="reinitialize"):
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
