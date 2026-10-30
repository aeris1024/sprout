import json
import sqlite3
import sys

import pytest

from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository, SCHEMA_VERSION


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob('*') if p.is_file()}


def saved(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    asset = repo.root / 'asset.bin'
    asset.write_bytes(b'precious data')
    repo.track([asset])
    repo.commit('base')
    return repo


def test_current_format_reopens_and_accepts_writes(tmp_path):
    repo = saved(tmp_path)
    reopened = Repository.discover(repo.root)
    (repo.root / 'asset.bin').write_bytes(b'next version')
    reopened.commit('next')
    with reopened.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '1'
    reopened.delete_commit(reopened.current_commit())
    item = reopened.trash_items()[0]
    with reopened.connect() as db:
        payload = json.loads(db.execute('SELECT payload FROM trash_entries WHERE id=?', (item['id'],)).fetchone()[0])
    assert payload['version'] == 1
    reopened.restore_trash(item['id'])
    assert Repository.discover(repo.root).doctor().ok


@pytest.mark.parametrize('statement,reason', [
    ("UPDATE meta SET value='0' WHERE key='schema_version'", 'schema_version'),
    ("UPDATE meta SET value='99' WHERE key='schema_version'", 'schema_version'),
    ("DELETE FROM meta WHERE key='schema_version'", 'schema_version'),
    ('DROP TABLE meta', 'unreadable_metadata'),
    ('DROP TABLE bud_files', 'missing_tables'),
    ('DROP INDEX idx_single_thumbnail', 'schema_structure'),
    ('ALTER TABLE commit_files DROP COLUMN mtime_ns', 'schema_structure'),
    ('ALTER TABLE commit_files ADD COLUMN unexpected TEXT', 'schema_structure'),
    ("DELETE FROM meta WHERE key='repository_id'", 'missing_metadata'),
    ("UPDATE meta SET value='future' WHERE key='object_compression'", 'object_compression'),
])
@pytest.mark.parametrize('command', [['status'], ['commit', '-m', 'must not write']])
@pytest.mark.parametrize('json_output', [False, True])
def test_invalid_db_cli_is_nonmutating(tmp_path, monkeypatch, capsys, statement,
                                           reason, command, json_output):
    repo = saved(tmp_path)
    with sqlite3.connect(repo.db_path) as db:
        db.execute(statement)
        db.commit()
        db.execute('PRAGMA journal_mode=DELETE')
    before = snapshot(repo.root)
    monkeypatch.chdir(repo.root)
    monkeypatch.setattr(sys, 'argv', ['sprout', *command] + (['--json'] if json_output else []))
    assert cli.main() == 1
    output = capsys.readouterr()
    assert not output.out
    if json_output:
        error = json.loads(output.err)
        assert error['code'] == 'unsupported_repository_format'
        assert error['details']['reason'] == reason
        assert error['details']['supported_schema_version'] == SCHEMA_VERSION
        message = error['message']
    else:
        message = output.err
    assert message
    assert "reinitialize" not in message
    assert snapshot(repo.root) == before


@pytest.mark.parametrize('version', [None, 99, '1', True])
@pytest.mark.parametrize('json_output', [False, True])
def test_unsupported_restore_record_cli_is_nonmutating(tmp_path, monkeypatch, capsys,
                                                        version, json_output):
    repo = saved(tmp_path)
    operation = repo.tmp / 'restore-future'
    (operation / 'backup').mkdir(parents=True)
    (operation / 'backup' / 'asset.bin').write_bytes(b'backup')
    (operation / 'plan.json').write_text(json.dumps({
        'version': version, 'actions': [], 'attempted': 0, 'rollback': None,
    }))
    repo._set_active_operation(operation.name)
    with sqlite3.connect(repo.db_path) as db:
        db.execute('PRAGMA journal_mode=DELETE')
    before = snapshot(repo.root)
    monkeypatch.chdir(repo.root)
    monkeypatch.setattr(sys, 'argv', ['sprout', 'status'] + (['--json'] if json_output else []))
    assert cli.main() == 1
    output = capsys.readouterr()
    if json_output:
        error = json.loads(output.err)
        assert error['code'] == 'unsupported_restore_plan_version'
        assert error['details'] == {'found_version': version, 'supported_version': 1}
    else:
        assert 'unsupported version; backups retained' in output.err
    assert snapshot(repo.root) == before
