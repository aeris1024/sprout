import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository, SCHEMA, SCHEMA_VERSION


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


def test_v1_definition_is_frozen():
    # Never silently redefine V1: the next incompatible format must be V2+.
    frozen = (Path(__file__).parent / 'fixtures/schema_v1.sql').read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == (
        '4a18c36f50c03eb633803947724071074d635910eae4eed0b4aec852d1ac75ec'
    )


@pytest.mark.parametrize("version", [1, 4])
def test_frozen_legacy_is_rejected_without_changes(tmp_path, version):
    root = tmp_path / 'legacy'
    control = root / '.sprout'
    control.mkdir(parents=True)
    (root / 'asset.bin').write_bytes(b'unsaved work')
    with sqlite3.connect(control / 'repository.db') as db:
        db.executescript((Path(__file__).parent / f'fixtures/schema_v{version}.sql').read_text())
        db.execute("INSERT INTO meta VALUES('schema_version', ?)", (str(version),))
    before = snapshot(root)
    with pytest.raises(SproutError) as error:
        Repository.discover(root)
    assert error.value.code == 'unsupported_repository_format'
    assert error.value.details['found_schema_version'] == str(version)
    assert snapshot(root) == before


def test_v4_definition_is_frozen():
    frozen = (Path(__file__).parent / 'fixtures/schema_v4.sql').read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == '817957f210c294ac81a52698a91133208ec7235110a171e669a629cc82fe9ff0'


def test_current_format_definition_is_frozen():
    assert SCHEMA_VERSION == '5'
    assert hashlib.sha256(SCHEMA.encode()).hexdigest() == (
        '2c42b4b943712732e60ae636379979fa2e0426b6fff9036226475ebda4479a87'
    )


def test_current_format_reopens_and_accepts_writes(tmp_path):
    repo = saved(tmp_path)
    reopened = Repository.discover(repo.root)
    (repo.root / 'asset.bin').write_bytes(b'next version')
    reopened.commit('next')
    assert Repository.discover(repo.root).doctor().ok


@pytest.mark.parametrize('statement,reason', [
    ("UPDATE meta SET value='0' WHERE key='schema_version'", 'schema_version'),
    ("UPDATE meta SET value='99' WHERE key='schema_version'", 'schema_version'),
    ("DELETE FROM meta WHERE key='schema_version'", 'schema_version'),
    ('DROP TABLE meta', 'unreadable_metadata'),
    ('DROP TABLE bud_files', 'missing_tables'),
    ('DROP INDEX idx_single_thumbnail', 'schema_structure'),
    ('ALTER TABLE commit_files DROP COLUMN mtime_ns', 'schema_structure'),
    ('ALTER TABLE commit_files ADD COLUMN legacy TEXT', 'schema_structure'),
    ("DELETE FROM meta WHERE key='repository_id'", 'missing_metadata'),
    ("UPDATE meta SET value='future' WHERE key='object_compression'", 'object_compression'),
])
@pytest.mark.parametrize('command', [['status'], ['commit', '-m', 'must not write']])
@pytest.mark.parametrize('json_output', [False, True])
def test_incompatible_db_cli_is_nonmutating(tmp_path, monkeypatch, capsys, statement,
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
    assert 'preserve the entire project including .sprout' in message
    assert 'reinitialize a separate copy' in message
    assert snapshot(repo.root) == before


@pytest.mark.parametrize('version', [None, 99, '1', True])
@pytest.mark.parametrize('json_output', [False, True])
def test_incompatible_restore_record_cli_is_nonmutating(tmp_path, monkeypatch, capsys,
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
