import json
import sqlite3

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository


TABLES = ('commits', 'commit_files', 'commit_attachments', 'commit_notes', 'commit_labels',
          'branches', 'repository_state', 'buds', 'bud_files', 'trash_entries', 'trash_objects')


def db_state(repo):
    with repo.connect() as db:
        return {table: sorted(tuple(row) for row in db.execute(f'SELECT * FROM {table}'))
                for table in TABLES}


def setup_history(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    commits = []
    for content in (b'first', b'middle', b'last'):
        file.write_bytes(content)
        if not commits:
            repo.track([file])
        commits.append(repo.commit(content.decode()).commit_id)
    return repo, file, commits


def preview(repo, tmp_path, name, content):
    source = tmp_path / name
    source.write_bytes(content)
    return repo.add_previews('main', [source])[0]


@pytest.mark.parametrize('index', [0, 1, 2])
def test_commit_recovery_restores_rows_references_and_keeps_work(tmp_path, index):
    repo, file, commits = setup_history(tmp_path)
    selected = commits[index]
    repo.create_branch('alias', start_point=selected)
    repo.restore(selected)
    repo.set_note(selected, 'note')
    repo.add_label(selected, 'label')
    source = tmp_path / 'preview.wav'
    source.write_bytes(b'preview')
    repo.add_previews(selected, [source])
    file.write_bytes(b'unsaved')
    repo.save_bud()
    before = db_state(repo)
    content = file.read_bytes(), file.stat().st_mtime_ns
    repo.delete_commit(selected)
    item = repo.trash_items()[0]
    repo = Repository.discover(repo.root)
    repo.gc()
    assert item['objects']
    after_delete = db_state(repo)
    assert repo.restore_trash(item['id'], dry_run=True)['dry_run']
    assert db_state(repo) == after_delete
    repo.restore_trash(item['id'])
    assert db_state(repo) == before
    assert (file.read_bytes(), file.stat().st_mtime_ns) == content
    assert repo.doctor().ok


def test_lone_root_recovery(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset'
    file.write_bytes(b'only')
    repo.track([file])
    only = repo.commit('only').commit_id
    repo.delete_commit(only)
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert repo.current_commit() == only
    assert repo.head_commit() == only
    assert repo.status() == []


@pytest.mark.parametrize('change', ['commit', 'branch_reuse', 'bud_removed', 'parent_removed'])
def test_later_operations_conflict_without_partial_restore(tmp_path, change):
    repo, file, commits = setup_history(tmp_path)
    repo.create_branch('alias', start_point=commits[-1])
    file.write_bytes(b'draft')
    bud = repo.save_bud()
    repo.delete_commit(commits[-1])
    item_id = repo.trash_items()[0]['id']
    if change == 'commit':
        repo.commit('new work')
    elif change == 'branch_reuse':
        repo.delete_branch('alias')
        repo.create_branch('alias')
    elif change == 'bud_removed':
        repo.drop_bud(bud.id)
    else:
        repo.delete_commit(commits[-2])
    before = db_state(repo)
    with pytest.raises(SproutError) as error:
        repo.restore_trash(item_id)
    assert error.value.code == 'trash_restore_conflict'
    assert db_state(repo) == before
    assert file.read_bytes() == b'draft'


def test_preview_delete_and_replacements_restore_original_identity_order_and_times(tmp_path):
    repo, file, commits = setup_history(tmp_path)
    first = preview(repo, tmp_path, 'one.wav', b'one')
    second = preview(repo, tmp_path, 'two.wav', b'two')
    third = preview(repo, tmp_path, 'three.wav', b'three')
    originals = repo.previews('main')
    repo.delete_preview('main', second.id)
    deletion = repo.trash_items()[0]['id']
    repo.gc()
    repo = Repository.discover(repo.root)
    repo.restore_trash(deletion)
    assert repo.previews('main') == originals
    source = tmp_path / 'replacement.wav'
    source.write_bytes(b'v2')
    v2 = repo.replace_preview('main', second.id, source)
    older = repo.trash_items()[0]['id']
    source.write_bytes(b'v3')
    repo.replace_preview('main', second.id, source)
    newer = repo.trash_items()[0]['id']
    before = db_state(repo)
    with pytest.raises(SproutError) as conflict:
        repo.restore_trash(older)
    assert conflict.value.code == 'trash_restore_conflict'
    assert db_state(repo) == before
    repo.gc()
    repo.restore_trash(newer)
    assert repo.preview('main', second.id) == v2
    repo.restore_trash(older)
    assert repo.previews('main') == [first, second, third]


@pytest.mark.parametrize('change', ['add', 'order', 'delete_commit'])
def test_preview_recovery_refuses_changed_context(tmp_path, change):
    repo, file, commits = setup_history(tmp_path)
    a = preview(repo, tmp_path, 'a.wav', b'a')
    b = preview(repo, tmp_path, 'b.wav', b'b')
    c = preview(repo, tmp_path, 'c.wav', b'c')
    repo.delete_preview('main', b.id)
    item_id = repo.trash_items()[0]['id']
    if change == 'add':
        preview(repo, tmp_path, 'new.wav', b'new')
    elif change == 'order':
        repo.reorder_previews('main', [c.id, a.id])
    else:
        repo.delete_commit(commits[-1])
    before = db_state(repo)
    with pytest.raises(SproutError) as error:
        repo.restore_trash(item_id)
    assert error.value.code == 'trash_restore_conflict'
    assert db_state(repo) == before


def test_purge_capacity_shared_protection_and_gc(tmp_path):
    repo, file, commits = setup_history(tmp_path)
    a = preview(repo, tmp_path, 'a.wav', b'shared preview')
    b = preview(repo, tmp_path, 'b.wav', b'shared preview')
    repo.delete_preview('main', a.id)
    first = repo.trash_items()[0]
    assert first['protected_bytes'] > 0 and first['reclaimable_bytes'] == 0
    repo.delete_preview('main', b.id)
    second = repo.trash_items()[0]
    assert second['reclaimable_bytes'] == 0
    before = db_state(repo)
    repo.purge_trash(first['id'], dry_run=True)
    assert db_state(repo) == before
    repo.purge_trash(first['id'])
    assert repo.trash_items()[0]['reclaimable_bytes'] > 0
    assert a.object_hash not in repo.gc().objects
    repo.purge_trash(second['id'])
    assert a.object_hash in repo.gc().objects
    assert repo.doctor().ok


@pytest.mark.parametrize('failure', ['delete', 'restore'])
def test_database_failure_is_atomic_and_reopens(tmp_path, failure):
    repo, file, commits = setup_history(tmp_path)
    if failure == 'restore':
        repo.delete_commit(commits[-1])
    before = db_state(repo)
    with repo.connect() as db:
        db.execute('CREATE TRIGGER fail_operation BEFORE ' +
                   ('DELETE ON commits' if failure == 'delete' else 'INSERT ON commits') +
                   " BEGIN SELECT RAISE(ABORT, 'stop'); END")
    with pytest.raises(SproutError):
        if failure == 'delete':
            repo.delete_commit(commits[-1])
        else:
            repo.restore_trash(repo.trash_items()[0]['id'])
    assert db_state(repo) == before
    with repo.connect() as db:
        db.execute('DROP TRIGGER fail_operation')
    assert Repository.discover(repo.root).doctor().ok


def test_prune_keeps_trash_objects_and_archive_excludes_deleted_commits(tmp_path):
    repo, file, commits = setup_history(tmp_path)
    deleted = repo.manifest(commits[1])['asset.bin'].object_hash
    repo.delete_commit(commits[1])
    output = tmp_path / 'archive'
    repo.archive(output)
    model = json.loads((output / 'archive.json').read_text())
    assert commits[1] not in {c['id'] for c in model['commits']}
    repo.prune(all_history=True)
    assert deleted not in repo.gc().objects
    assert repo.trash_items()


def test_cli_trash_confirmation_json_restore_and_purge(tmp_path, monkeypatch):
    repo, file, commits = setup_history(tmp_path)
    monkeypatch.chdir(repo.root)
    repo.delete_commit(commits[-1])
    runner = CliRunner()
    items = json.loads(runner.invoke(app, ['trash', 'list', '--json']).stdout)
    item_id = items[0]['id']
    assert json.loads(runner.invoke(app, ['trash', 'show', item_id, '--json']).stdout)['id'] == item_id
    for action in ('restore', 'purge'):
        assert json.loads(runner.invoke(app, ['trash', action, item_id, '--dry-run', '--json']).stdout)['dry_run']
    denied = runner.invoke(app, ['trash', 'purge', item_id, '--json'])
    assert denied.exit_code != 0
    assert denied.exception.code == 'trash_confirmation_required'
    assert runner.invoke(app, ['trash', 'restore', item_id, '--json']).exit_code == 0
    assert repo.current_commit() == commits[-1]
    repo.delete_commit(commits[-1])
    item_id = repo.trash_items()[0]['id']
    assert runner.invoke(app, ['trash', 'purge', item_id, '--yes', '--json']).exit_code == 0
    assert repo.trash_items() == []


def test_interruption_before_commit_keeps_original_and_no_partial_trash(tmp_path, monkeypatch):
    from sprout import trash
    repo, file, commits = setup_history(tmp_path)
    before = db_state(repo)
    record = trash.record
    def interrupt(*args, **kwargs):
        record(*args, **kwargs)
        raise KeyboardInterrupt('after record, before commit')
    with monkeypatch.context() as context:
        context.setattr(trash, 'record', interrupt)
        with pytest.raises(KeyboardInterrupt):
            repo.delete_commit(commits[-1])
    assert db_state(repo) == before
    assert Repository.discover(repo.root).doctor().ok


def test_invalid_trash_record_is_retained_and_reported(tmp_path):
    repo, file, commits = setup_history(tmp_path)
    repo.delete_commit(commits[-1])
    item_id = repo.trash_items()[0]['id']
    with repo.connect() as db:
        db.execute("UPDATE trash_entries SET payload=?", (json.dumps({'version': 99}),))
    before = db_state(repo)
    with pytest.raises(SproutError) as error:
        repo.restore_trash(item_id)
    assert error.value.code == 'invalid_trash_record'
    assert 'invalid_trash_record' in {issue.kind for issue in repo.doctor().issues}
    assert db_state(repo) == before
    assert repo.gc().removed_objects == 0


def test_restore_interruption_rolls_back_metadata_and_retains_record(tmp_path, monkeypatch):
    from sprout import trash
    repo, file, commits = setup_history(tmp_path)
    repo.delete_commit(commits[-1])
    item_id = repo.trash_items()[0]['id']
    before = db_state(repo)
    restore = trash.restore
    def interrupt(*args):
        restore(*args)
        raise KeyboardInterrupt('after restored rows, before commit')
    with monkeypatch.context() as context:
        context.setattr(trash, 'restore', interrupt)
        with pytest.raises(KeyboardInterrupt):
            repo.restore_trash(item_id)
    assert db_state(repo) == before
    reopened = Repository.discover(repo.root)
    reopened.restore_trash(item_id)
    assert reopened.current_commit() == commits[-1]


def test_unrelated_edits_survive_middle_commit_recovery(tmp_path):
    repo, file, commits = setup_history(tmp_path)
    repo.delete_commit(commits[1])
    item_id = repo.trash_items()[0]['id']
    repo.set_note(commits[0], 'later unrelated note')
    file.write_bytes(b'later content')
    newer = repo.commit('newer tip').commit_id
    repo.restore_trash(item_id)
    assert repo.current_commit() == newer
    assert repo.commit_info(commits[1])[0]['parent_id'] == commits[0]
    assert repo.annotations(commits[0]).note == 'later unrelated note'
    assert file.read_bytes() == b'later content'


def test_trash_order_survives_clock_rollback_and_vacuum(tmp_path):
    repo, file, commits = setup_history(tmp_path)
    a = preview(repo, tmp_path, 'a.wav', b'a')
    b = preview(repo, tmp_path, 'b.wav', b'b')
    repo.delete_preview('main', a.id)
    older = repo.trash_items()[0]['id']
    repo.delete_preview('main', b.id)
    newer = repo.trash_items()[0]['id']
    with repo.connect() as db:
        db.execute("UPDATE trash_entries SET created_at='2000-01-01T00:00:00.000000+00:00' WHERE id=?", (newer,))
    with repo.connect() as db:
        db.execute('VACUUM')
    assert [item['id'] for item in Repository.discover(repo.root).trash_items()] == [newer, older]
    repo.restore_trash(newer)
    repo.restore_trash(older)
    assert repo.previews('main') == [a, b]
