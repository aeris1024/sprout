"""Canonical maintenance/trash behavior through CLI and the unchanged serve protocol."""
import io
import json

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command, serve


def call(*args):
    response = run_command(app, [*args, '--json'])
    assert response['ok'], response
    return response['result']


@pytest.fixture
def history(tmp_path, monkeypatch):
    repository = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repository.root)
    source = repository.root / 'asset.bin'
    source.write_bytes(b'first')
    repository.track([source])
    first = repository.commit('first').commit_id
    source.write_bytes(b'second')
    second = repository.commit('second').commit_id
    return repository, source, first, second


def test_maintenance_commands_preserve_json_and_working_files(history):
    repository, source, _, _ = history
    before = source.read_bytes()
    for operation in ['stats', 'doctor', 'gc']:
        arguments = ['--dry-run'] if operation == 'gc' else []
        canonical = call('maintenance', operation, *arguments)
        retired = run_command(app, [operation, *arguments, '--json'])
        assert not retired['ok'] and retired['error']['code'] == 'usage_error'
        direct = CliRunner().invoke(app, ['maintenance', operation, *arguments, '--json'])
        assert direct.exit_code == 0
        assert json.loads(direct.stdout) == canonical
    assert source.read_bytes() == before
    assert repository.doctor().ok


def test_doctor_report_preserves_failure_exit_code(history):
    repository, _, first, _ = history
    digest = next(iter(repository.manifest(first).values())).object_hash
    repository._object_path(digest).unlink()
    failed = run_command(app, ['maintenance', 'doctor', '--json'])
    assert not failed['ok'] and failed['exit_code'] == 1
    assert failed['result']['ok'] is False
    assert call('maintenance', 'doctor', '--report')['ok'] is False


def test_gc_keeps_commits_buds_and_trash_until_purged(history, tmp_path):
    repository, source, _, second = history
    source.write_bytes(b'only in bud')
    bud = repository.save_bud()
    repository.delete_commit(second)
    item = call('trash', 'list')[0]
    orphan = tmp_path / 'orphan.bin'
    orphan.write_bytes(b'not referenced')
    digest, _ = repository._store_object(orphan)
    plan = call('maintenance', 'gc', '--dry-run')
    assert plan['objects'] == [digest]
    assert repository._object_path(digest).exists()
    assert call('maintenance', 'gc')['removed_objects'] == 1
    assert call('trash', 'list')[0]['id'] == item['id']
    assert repository.buds()[0].id == bud.id
    assert repository.doctor().ok


def test_trash_subcommands_keep_confirmation_dry_run_exact_ids_and_conflicts(history):
    repository, source, _, second = history
    repository.delete_commit(second)
    item = call('trash', 'list')[0]
    assert not run_command(app, ['trash', '--json'])['ok']
    assert call('trash', 'show', item['id'])['id'] == item['id']
    for operation in ['restore', 'purge']:
        assert call('trash', operation, item['id'], '--dry-run')['dry_run']
        assert call('trash', 'list')[0]['id'] == item['id']
    refused = run_command(app, ['trash', 'purge', item['id'], '--json'])
    assert refused['error']['code'] == 'trash_confirmation_required'
    assert not run_command(app, ['trash', 'show', item['id'][:8], '--json'])['ok']
    source.write_bytes(b'new history')
    repository.commit('new tip')
    conflict = run_command(app, ['trash', 'restore', item['id'], '--json'])
    assert not conflict['ok']
    assert call('trash', 'list')[0]['id'] == item['id']
    assert source.read_bytes() == b'new history'
    assert call('trash', 'purge', item['id'], '--yes')['id'] == item['id']
    assert call('trash', 'list') == []


def test_serve_protocol_dispatches_nested_commands_without_changing_errors(history):
    _, _, _, _ = history
    arguments = [
        ['maintenance', 'stats', '--json'],
        ['maintenance', 'doctor', '--json'],
        ['trash', 'list', '--json'],
        ['trash', 'show', 'missing', '--json'],
        ['status', '--json'],
    ]
    source = io.StringIO(''.join(json.dumps({'id': i, 'args': args}) + '\n' for i, args in enumerate(arguments)))
    sink = io.StringIO()
    serve(app, 'test', source, sink)
    responses = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert responses[0] == {'ready': True, 'version': 'test', 'protocol': 1}
    for i, args in enumerate(arguments):
        assert responses[i + 1] == {'id': i, **run_command(app, args)}


def test_maintenance_and_trash_help_expose_operations():
    for group, operations in [('maintenance', ['stats', 'doctor', 'gc']), ('trash', ['list', 'show', 'restore', 'purge'])]:
        result = CliRunner().invoke(app, [group, '--help'])
        assert result.exit_code == 0
        for operation in operations:
            assert operation in result.stdout
