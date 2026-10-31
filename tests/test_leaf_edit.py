"""Description updates are atomic and independent of snapshots and labels."""
import sqlite3

import pytest

from sprout import trash
from sprout.cli import app
from sprout.repository import NOTE_MAX_CHARS, Repository
from sprout.serve import run_command


@pytest.fixture
def leaf(tmp_path, monkeypatch):
    repository = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repository.root)
    source = repository.root / 'asset.bin'
    source.write_bytes(b'original')
    repository.track([source])
    identifier = repository.commit('original message').commit_id
    repository.set_note(identifier, 'original note')
    repository.add_label(identifier, 'reviewed')
    return repository, source, identifier


def call(*args):
    response = run_command(app, [*args, '--json'])
    assert response['ok'], response
    return response['result']


def test_edit_both_fields_preserves_snapshot_labels_and_v1(leaf):
    repository, source, identifier = leaf
    manifest = repository.manifest(identifier)
    updated = call('leaf', 'edit', identifier, '--message', ' new message ', '--note', ' new\nnote ')
    assert updated['commit_id'] == identifier
    assert updated['message'] == 'new message'
    assert updated['note'] == 'new\nnote'
    assert updated['labels'] == ['reviewed']
    shown = call('leaf', 'show', identifier)
    assert (shown['message'], shown['note'], shown['parent_id']) == ('new message', 'new\nnote', None)
    assert repository.manifest(identifier) == manifest
    assert source.read_bytes() == b'original'
    assert repository.current_commit() == repository.head_commit() == identifier
    with repository.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '1'


def test_edit_omitted_fields_and_clear_note_recovery(leaf):
    repository, _, identifier = leaf
    before = repository.annotations(identifier)
    changed = call('leaf', 'edit', identifier, '--message', 'message only')
    assert changed['note'] == before.note and changed['note_updated_at'] == before.note_updated_at
    changed = call('leaf', 'edit', identifier, '--note', 'note only')
    assert changed['message'] == 'message only'
    changed = call('leaf', 'edit', identifier, '--clear-note')
    assert changed['note'] is None and changed['note_updated_at'] is None
    recovery = repository.trash_items()[0]
    assert recovery['kind'] == 'note_delete'
    repository.restore_trash(recovery['id'])
    assert repository.annotations(identifier).note == 'note only'
    assert call('leaf', 'show', identifier)['message'] == 'message only'
    assert repository.annotations(identifier).labels == ('reviewed',)


@pytest.mark.parametrize('arguments,code', [
    ([], 'no_edit_fields'),
    (['--message', '  ', '--note', 'valid'], 'empty_message'),
    (['--message', 'valid', '--note', 'n' * (NOTE_MAX_CHARS + 1)], 'note_too_long'),
    (['--note', 'text', '--clear-note'], 'conflicting_note_options'),
])
def test_invalid_edits_change_neither_field(leaf, arguments, code):
    repository, _, identifier = leaf
    before = call('leaf', 'show', identifier)
    result = run_command(app, ['leaf', 'edit', identifier, *arguments, '--json'])
    assert result['error']['code'] == code
    assert call('leaf', 'show', identifier) == before
    assert repository.trash_items() == []


def test_storage_failure_rolls_back_message_as_well_as_note(leaf):
    repository, _, identifier = leaf
    before = call('leaf', 'show', identifier)
    with repository.connect() as db:
        db.execute("CREATE TRIGGER deny_note BEFORE INSERT ON commit_notes BEGIN SELECT RAISE(ABORT,'storage failure'); END")
    result = run_command(app, ['leaf', 'edit', identifier, '--message', 'new', '--note', 'new', '--json'])
    assert result['error']['code'] == 'repository_error'
    assert call('leaf', 'show', identifier) == before


def test_recovery_failure_rolls_back_note_deletion_and_message(leaf, monkeypatch):
    repository, _, identifier = leaf
    before = call('leaf', 'show', identifier)
    record = trash.record

    def fail_after_record(*args, **kwargs):
        record(*args, **kwargs)
        raise sqlite3.OperationalError('recovery storage failure')

    monkeypatch.setattr(trash, 'record', fail_after_record)
    result = run_command(app, ['leaf', 'edit', identifier, '--message', 'new', '--clear-note', '--json'])
    assert result['error']['code'] == 'repository_error'
    assert call('leaf', 'show', identifier) == before
    assert repository.trash_items() == []


def test_empty_note_keeps_existing_delete_semantics_and_note_limit(leaf):
    repository, _, identifier = leaf
    assert call('leaf', 'edit', identifier, '--note', 'n' * NOTE_MAX_CHARS)['note'] == 'n' * NOTE_MAX_CHARS
    assert call('leaf', 'edit', identifier, '--note', ' ')['note'] is None
    assert len(repository.trash_items()) == 1
    assert not run_command(app, ['leaf', 'note', '--help'])['ok']
