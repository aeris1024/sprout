"""Regression tests for restore boundaries, topology changes and durable undo."""
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository


class Interrupted(BaseException):
    pass


def write(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def repo(tmp_path, monkeypatch):
    repository = Repository.init(tmp_path / "project")
    monkeypatch.chdir(repository.root)
    return repository


def topology(repo):
    asset = write(repo.root, "asset", b"file")
    repo.track([asset])
    first = repo.commit("file").commit_id
    repo.create_branch("file-version")
    asset.unlink()
    repo.untrack([asset])
    child = write(repo.root, "asset/deep/data", b"child")
    repo.track([child])
    second = repo.commit("directory").commit_id
    return first, second


def state(repo):
    files = {}
    dirs = set()
    for path in repo.root.rglob("*"):
        relative = path.relative_to(repo.root).as_posix()
        if relative == ".sprout" or relative.startswith(".sprout/"):
            continue
        if path.is_file():
            files[relative] = (path.read_bytes(), path.stat().st_mtime_ns)
        elif path.is_dir():
            dirs.add(relative)
    return files, dirs, repo.tracked(), repo.head_branch(), repo.head_commit()


def active(repo):
    with repo.connect() as db:
        return db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()[0]


@pytest.fixture(params=["junction", "symlink"])
def directory_link(request):
    links = []
    def create(target, link):
        if request.param == "junction":
            if os.name != "nt":
                pytest.skip("Windows junctions only")
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        else:
            try:
                os.symlink(target, link, target_is_directory=True)
            except OSError as exc:
                pytest.skip(f"symlink creation unavailable: {exc}")
        links.append(link)
    yield create
    for link in links:
        if link.is_symlink():
            link.unlink()
        elif link.is_junction():
            link.rmdir()


@pytest.mark.parametrize("operation", ["restore", "discard", "partial", "switch", "branch", "implicit-branch"])
@pytest.mark.parametrize("inside", [False, True])
def test_links_are_rejected_before_hashing(repo, tmp_path, monkeypatch, directory_link, operation, inside):
    file = write(repo.root, "assets/data", b"saved")
    repo.track([file])
    repo.commit("saved")
    repo.create_branch("other")
    file.unlink()
    file.parent.rmdir()
    external = (repo.root if inside else tmp_path) / "external"
    data = write(external, "data", b"do not touch")
    before = (data.read_bytes(), data.stat().st_mtime_ns)
    directory_link(external, repo.root / "assets")
    def no_hash(*args, **kwargs):
        pytest.fail("unsafe working path was hashed")
    monkeypatch.setattr(repo, "hash_file", no_hash)
    with pytest.raises(SproutError) as error:
        if operation == "switch":
            repo.switch("other")
        elif operation == "branch":
            repo.create_branch("new", start_point="main", switch=True)
        elif operation == "implicit-branch":
            repo.create_branch("new", switch=True)
        else:
            repo.restore("main", [Path("assets/data")] if operation == "partial" else None,
                         discard=operation == "discard")
    assert error.value.code == "unsafe_restore_path"
    assert (data.read_bytes(), data.stat().st_mtime_ns) == before
    assert not active(repo)
    assert "new" not in {row[0] for row in repo.branches()}


def test_dangling_file_link_is_rejected(repo, tmp_path):
    file = write(repo.root, "data", b"saved")
    repo.track([file])
    repo.commit("saved")
    file.unlink()
    try:
        file.symlink_to(tmp_path / "missing")
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    try:
        with pytest.raises(SproutError) as error:
            repo.restore("main", discard=True)
        assert error.value.code == "unsafe_restore_path"
        assert file.is_symlink()
    finally:
        file.unlink()


def test_topology_roundtrip_and_branch_switch(repo):
    first, second = topology(repo)
    directory_state = state(repo)
    repo.restore(first)
    assert (repo.root / "asset").read_bytes() == b"file"
    assert repo.tracked() == {"asset"}
    assert repo.head_commit() == second
    repo.restore(second)
    assert state(repo) == directory_state
    repo.switch("file-version")
    assert repo.head_commit() == first
    repo.switch("main")
    assert state(repo) == directory_state
    repo.create_branch("past", start_point=first, switch=True)
    assert (repo.root / "asset").read_bytes() == b"file"
    assert repo.head_branch() == "past"


@pytest.mark.parametrize("extra", ["file", "empty", "nested-empty"])
def test_topology_preserves_untracked_entries(repo, extra):
    first, _ = topology(repo)
    if extra == "file":
        write(repo.root, "asset/extra", b"untracked")
    else:
        (repo.root / "asset" / ("extra/deep" if extra == "nested-empty" else "extra")).mkdir(parents=True)
    before = state(repo)
    with pytest.raises(SproutError, match="untracked path"):
        repo.restore(first, discard=True)
    assert state(repo) == before
    assert not active(repo)


@pytest.mark.parametrize("reverse", [False, True])
def test_partial_topology_never_expands_scope(repo, reverse):
    first, second = topology(repo)
    target = first
    if reverse:
        repo.restore(first)
        target = second
    before = state(repo)
    with pytest.raises(SproutError) as error:
        repo.restore(target, [Path("asset")], discard=True)
    assert error.value.code == "restore_scope_conflict"
    assert state(repo) == before


@pytest.mark.parametrize("kind,reverse", [("backup", False), ("rmdir", False), ("mkdir", True), ("install", False)])
@pytest.mark.parametrize("after", [False, True])
@pytest.mark.parametrize("interrupt", [False, True])
def test_failure_at_each_action_restores_original_state(repo, monkeypatch, kind, reverse, after, interrupt):
    first, second = topology(repo)
    target = first
    if reverse:
        repo.restore(first)
        target = second
    before = state(repo)
    original = repo._apply_restore_action
    def fail(directory, action):
        if action["kind"] != kind:
            return original(directory, action)
        if after:
            original(directory, action)
        raise Interrupted() if interrupt else OSError("injected failure")
    monkeypatch.setattr(repo, "_apply_restore_action", fail)
    with pytest.raises(Interrupted if interrupt else OSError):
        repo.restore(target)
    if interrupt:
        assert active(repo)
        repo = Repository.discover(repo.root)
    assert state(repo) == before
    assert not active(repo)


@pytest.mark.parametrize("point", ["utime", "database"])
def test_topology_metadata_failure(repo, monkeypatch, point):
    first, _ = topology(repo)
    before = state(repo)
    if point == "utime":
        original = os.utime
        def fail(path, *args, **kwargs):
            if Path(path) == repo.root / "asset":
                raise OSError("timestamp failure")
            return original(path, *args, **kwargs)
        monkeypatch.setattr(os, "utime", fail)
    else:
        def fail(*args, **kwargs):
            raise sqlite3.OperationalError("database failure")
        monkeypatch.setattr(repo, "_finalize_materialization", fail)
    with pytest.raises((OSError, sqlite3.Error)):
        repo.restore(first)
    assert state(repo) == before


@pytest.mark.parametrize("reverse", [False, True])
def test_recovery_can_be_interrupted_after_every_undo(repo, monkeypatch, reverse):
    first, second = topology(repo)
    target = first
    if reverse:
        repo.restore(first)
        target = second
    before = state(repo)
    def interrupt(*args, **kwargs):
        raise Interrupted()
    monkeypatch.setattr(repo, "_finalize_materialization", interrupt)
    with pytest.raises(Interrupted):
        repo.restore(target)
    undo = Repository._undo_restore_action
    seen = set()
    def interrupt_undo(self, directory, action):
        undo(self, directory, action)
        key = (action["kind"], action["path"])
        if key not in seen:
            seen.add(key)
            raise Interrupted()
    monkeypatch.setattr(Repository, "_undo_restore_action", interrupt_undo)
    for _ in range(20):
        try:
            recovered = Repository.discover(repo.root)
            break
        except Interrupted:
            assert active(repo)
    else:
        pytest.fail("recovery did not finish")
    assert state(recovered) == before
    assert not active(recovered)


def test_recovery_retains_backups_on_new_file_conflict(repo, monkeypatch):
    first, _ = topology(repo)
    def interrupt(*args, **kwargs):
        raise Interrupted()
    monkeypatch.setattr(repo, "_finalize_materialization", interrupt)
    with pytest.raises(Interrupted):
        repo.restore(first)
    operation = repo.tmp / active(repo)
    (repo.root / "asset").write_bytes(b"new work")
    with pytest.raises(SproutError) as error:
        Repository.discover(repo.root)
    assert error.value.code == "restore_recovery_conflict"
    assert (repo.root / "asset").read_bytes() == b"new work"
    assert (operation / "backup/asset/deep/data").read_bytes() == b"child"
    assert active(repo)


def test_recovery_refuses_replaced_parent_link(repo, tmp_path, monkeypatch, directory_link):
    file = write(repo.root, "assets/data", b"original")
    repo.track([file])
    first = repo.commit("original").commit_id
    file.write_bytes(b"new")
    repo.commit("new")
    def interrupt(*args, **kwargs):
        raise Interrupted()
    monkeypatch.setattr(repo, "_finalize_materialization", interrupt)
    with pytest.raises(Interrupted):
        repo.restore(first)
    operation = repo.tmp / active(repo)
    file.unlink()
    file.parent.rmdir()
    external = tmp_path / "external"
    data = write(external, "data", b"external")
    before = data.stat().st_mtime_ns
    directory_link(external, repo.root / "assets")
    with pytest.raises(SproutError) as error:
        Repository.discover(repo.root)
    assert error.value.code == "unsafe_restore_path"
    assert data.read_bytes() == b"external" and data.stat().st_mtime_ns == before
    assert (operation / "backup/assets/data").read_bytes() == b"new"
    assert active(repo)


@pytest.mark.parametrize("relative", ["../escape", ".SPROUT/repository.db" if os.name == "nt" else ".sprout/repository.db", "C:/escape", "/escape"])
def test_invalid_snapshot_paths_rejected(repo, relative):
    from sprout.repository import FileState
    with pytest.raises(SproutError) as error:
        repo._materialize({relative: FileState(relative, "0" * 64, 0, 0)})
    assert error.value.code == "unsafe_restore_path"


def test_linked_operation_storage_rejected(repo, tmp_path, directory_link):
    file = write(repo.root, "data", b"saved")
    repo.track([file])
    repo.commit("saved")
    repo.tmp.rmdir()
    external = tmp_path / "storage"
    external.mkdir()
    directory_link(external, repo.tmp)
    with pytest.raises(SproutError) as error:
        repo.restore("main", discard=True)
    assert error.value.code == "unsafe_restore_path"
    assert list(external.iterdir()) == []


def test_cli_scope_error_is_structured(repo, monkeypatch, capsys):
    first, _ = topology(repo)
    monkeypatch.setattr(sys, "argv", ["sprout", "restore", first, "asset", "--discard", "--json"])
    assert cli.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    payload = json.loads(output.err)
    assert payload["code"] == "restore_scope_conflict"
    assert payload["details"]["path"] == "asset/deep/data"


def test_cli_link_error_is_structured(repo, tmp_path, directory_link, monkeypatch, capsys):
    file = write(repo.root, "assets/data", b"saved")
    repo.track([file])
    repo.commit("saved")
    file.unlink()
    file.parent.rmdir()
    external = tmp_path / "external"
    external.mkdir()
    directory_link(external, repo.root / "assets")
    monkeypatch.setattr(sys, "argv", ["sprout", "restore", "main", "--discard", "--json"])
    assert cli.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    payload = json.loads(output.err)
    assert payload["code"] == "unsafe_restore_path"
    assert payload["details"]["path"] == "assets/data"


@pytest.mark.parametrize("version", [None, 2, 99, "1", True])
def test_unsupported_recovery_preserves_work_and_backup(repo, version):
    file = write(repo.root, "data", b"original")
    repo.track([file])
    repo.commit("original")
    operation = repo.tmp / "restore-unsupported"
    backup = operation / "backup"
    backup.mkdir(parents=True)
    os.replace(file, backup / "data")
    file.write_bytes(b"new unsaved work")
    plan = ({"new_paths": ["data"]} if version is None else
            {"version": version, "actions": [], "attempted": 0, "rollback": None})
    (operation / "plan.json").write_text(json.dumps(plan))
    repo._set_active_operation(operation.name)
    before = state(repo)
    saved = {p.relative_to(operation): p.read_bytes() for p in operation.rglob("*") if p.is_file()}
    for _ in range(2):
        with pytest.raises(SproutError, match="invalid restore recovery plan"):
            Repository.discover(repo.root)
        assert state(repo) == before
        assert active(repo) == operation.name
        assert {p.relative_to(operation): p.read_bytes() for p in operation.rglob("*") if p.is_file()} == saved


def test_recovery_preserves_unknown_work(repo, monkeypatch):
    file = write(repo.root, "data", b"original")
    repo.track([file])
    original = repo.commit("original").commit_id
    file.write_bytes(b"replacement")
    repo.commit("replacement")
    apply = repo._apply_restore_action
    def interrupt(directory, action):
        apply(directory, action)
        if action["kind"] == "install":
            raise Interrupted()
    with monkeypatch.context() as context:
        context.setattr(repo, "_apply_restore_action", interrupt)
        with pytest.raises(Interrupted):
            repo.restore(original)
    file.write_bytes(b"new unsaved work")
    operation = repo.tmp / active(repo)
    before = state(repo)
    with pytest.raises(SproutError) as error:
        Repository.discover(repo.root)
    assert error.value.code == "restore_recovery_conflict"
    assert state(repo) == before
    assert (operation / "backup" / "data").read_bytes() == b"replacement"
    assert active(repo) == operation.name


def test_recovery_restarts_after_interrupted_undo(repo, monkeypatch):
    file = write(repo.root, "data", b"original")
    repo.track([file])
    original = repo.commit("original").commit_id
    file.write_bytes(b"replacement")
    repo.commit("replacement")
    file.write_bytes(b"unsaved original")
    apply = repo._apply_restore_action
    def interrupt_install(directory, action):
        apply(directory, action)
        if action["kind"] == "install":
            raise Interrupted()
    with monkeypatch.context() as context:
        context.setattr(repo, "_apply_restore_action", interrupt_install)
        with pytest.raises(Interrupted):
            repo.restore(original, discard=True)
    operation = repo.tmp / active(repo)
    assert json.loads((operation / "plan.json").read_text())["version"] == 1
    undo = Repository._undo_restore_action
    def interrupt_undo(self, directory, action):
        undo(self, directory, action)
        raise Interrupted()
    with monkeypatch.context() as context:
        context.setattr(Repository, "_undo_restore_action", interrupt_undo)
        with pytest.raises(Interrupted):
            Repository.discover(repo.root)
    assert (operation / "backup" / "data").read_bytes() == b"unsaved original"
    Repository.discover(repo.root)
    assert file.read_bytes() == b"unsaved original"
    assert not active(repo)


def test_missing_tracked_file_stays_missing_after_failed_restore(repo, monkeypatch):
    file = write(repo.root, "data", b"saved")
    repo.track([file])
    repo.commit("saved")
    file.unlink()
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("injected failure")
    monkeypatch.setattr(repo, "_finalize_materialization", fail)
    with pytest.raises(sqlite3.OperationalError):
        repo.restore("main", discard=True)
    assert not file.exists()
    assert repo.tracked() == {"data"}


@pytest.mark.parametrize("create", [False, True])
def test_committed_database_is_never_rolled_back(repo, monkeypatch, create):
    first, _ = topology(repo)
    finalize = repo._finalize_materialization
    def fail_after_commit(*args, **kwargs):
        finalize(*args, **kwargs)
        raise OSError("error after commit")
    monkeypatch.setattr(repo, "_finalize_materialization", fail_after_commit)
    with pytest.raises(OSError, match="after commit"):
        if create:
            repo.create_branch("new", start_point=first, switch=True)
        else:
            repo.switch("file-version")
    assert repo.head_commit() == first
    assert repo.head_branch() == ("new" if create else "file-version")
    assert repo.tracked() == {"asset"}
    assert (repo.root / "asset").read_bytes() == b"file"
    assert not active(repo)


@pytest.mark.parametrize("after", [False, True])
def test_journal_write_failure_uses_durable_progress(repo, monkeypatch, after):
    first, _ = topology(repo)
    before = state(repo)
    original = repo._write_operation_plan
    failed = False
    def fail(path, plan):
        nonlocal failed
        if plan["attempted"] == 2 and not failed:
            failed = True
            if after:
                original(path, plan)
            raise OSError("checkpoint failure")
        return original(path, plan)
    monkeypatch.setattr(repo, "_write_operation_plan", fail)
    with pytest.raises(OSError, match="checkpoint failure"):
        repo.restore(first)
    assert state(repo) == before
    assert not active(repo)


def test_unsafe_plan_cannot_escape_operation(repo, tmp_path):
    external = write(tmp_path, "outside", b"external")
    operation = repo.tmp / "restore-interrupted"
    operation.mkdir()
    (operation / "plan.json").write_text(json.dumps({"version": 1, "actions": [{"kind": "mkdir", "path": "../outside"}], "attempted": 1, "rollback": None}))
    repo._set_active_operation(operation.name)
    with pytest.raises(SproutError) as error:
        Repository.discover(repo.root)
    assert error.value.code == "unsafe_restore_path"
    assert external.read_bytes() == b"external"
    assert active(repo)


def test_unsafe_link_in_backup_is_not_followed(repo, tmp_path, directory_link):
    operation = repo.tmp / "restore-interrupted"
    operation.mkdir()
    external = tmp_path / "external"
    data = write(external, "data", b"external")
    directory_link(external, operation / "backup")
    (operation / "plan.json").write_text(json.dumps({"version": 1, "actions": [], "attempted": 0, "rollback": None}))
    repo._set_active_operation(operation.name)
    with pytest.raises(SproutError) as error:
        Repository.discover(repo.root)
    assert error.value.code == "unsafe_restore_path"
    assert data.read_bytes() == b"external"
    assert active(repo)


@pytest.mark.parametrize("after", [False, True])
def test_registration_error_does_not_leave_unrecoverable_metadata(repo, monkeypatch, after):
    first, _ = topology(repo)
    before = state(repo)
    original = repo._set_active_operation
    def fail(value):
        if value:
            if after:
                original(value)
            raise OSError("registration failure")
        original(value)
    monkeypatch.setattr(repo, "_set_active_operation", fail)
    with pytest.raises(OSError, match="registration failure"):
        repo.restore(first)
    assert not active(repo)
    assert state(repo) == before
    Repository.discover(repo.root)
