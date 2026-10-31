"""Branch/path changes and immutable-file saved records share one CLI entry."""
import json

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


runner = CliRunner()


def history(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repo.root)
    asset, other = repo.root / 'asset.bin', repo.root / 'other.bin'
    asset.write_bytes(b'asset'); other.write_bytes(b'other')
    repo.track([asset, other])
    first = repo.commit('first').commit_id
    identity = repo.manifest(first)['asset.bin'].file_id
    other.write_bytes(b'changed')
    unchanged = repo.commit('asset unchanged').commit_id
    repo.move(asset, repo.root / 'renamed.bin')
    renamed = repo.commit('asset renamed').commit_id
    repo.create_branch('side', start_point=first, switch=True)
    asset.write_bytes(b'side version')
    side = repo.commit('side variant').commit_id
    repo.switch('main')
    repo.delete_branch('side')
    repo.add_label(first, 'Approved')
    repo.add_label(unchanged, 'approved')
    repo.add_label(renamed, 'Approved')
    repo.set_note(first, 'Review notes')
    return repo, identity, first, unchanged, renamed, side


def json_call(*args):
    result = runner.invoke(app, [*args, '--json'])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def test_leaf_list_preserves_branch_path_and_label_search(tmp_path, monkeypatch):
    repo, identity, first, unchanged, renamed, side = history(tmp_path, monkeypatch)
    rows = json_call('leaf', 'list')
    assert [row['id'] for row in rows] == [renamed, unchanged, first]
    assert rows == json_call('log')
    assert [row['id'] for row in json_call('leaf', 'list', 'renamed.bin')] == [renamed]
    assert [row['id'] for row in json_call('leaf', 'list', 'asset.bin')] == [renamed, first]
    approved = json_call('leaf', 'list', '--label', ' Approved ')
    assert [row['id'] for row in approved] == [renamed, first]
    assert approved[-1]['note'] == 'Review notes'
    assert approved[-1]['note_updated_at']
    assert [row['id'] for row in json_call('leaf', 'list', '--label', 'approved')] == [unchanged]
    assert [row['id'] for row in json_call('leaf', 'list', 'asset.bin', '--label', 'Approved', '-n', '1')] == [renamed]
    assert json_call('leaf', 'list', 'never.bin') == []
    missing = runner.invoke(app, ['leaf', 'list', 'never.bin'])
    assert missing.exit_code == 0 and 'No history for path: never.bin' in missing.stdout
    summary = runner.invoke(app, ['leaf', 'list', '-n', '2', '--oneline'])
    assert summary.stdout.splitlines() == [f'{renamed[:12]} asset renamed', f'{unchanged[:12]} asset unchanged']


def test_file_id_mode_preserves_all_branch_saved_records_and_json_shape(tmp_path, monkeypatch):
    repo, identity, first, unchanged, renamed, side = history(tmp_path, monkeypatch)
    records = json_call('leaf', 'list', '--file-id', identity)
    assert records == repo.file_history(identity)
    assert not run_command(app, ['file-history', identity, '--json'])['ok']
    assert records == json_call('log', '--file-id', identity)
    assert [row['commit_id'] for row in records] == [side, renamed, unchanged, first]
    assert [row['path'] for row in records] == ['asset.bin', 'renamed.bin', 'asset.bin', 'asset.bin']
    assert set(records[0]) == {'commit_id', 'created_at', 'message', 'path', 'file_id', 'object_hash', 'size', 'mtime_ns'}
    assert records[1]['object_hash'] == records[2]['object_hash'] == records[3]['object_hash']
    assert json_call('leaf', 'list', '--file-id', identity, '-n', '2') == records[:2]
    summary = runner.invoke(app, ['leaf', 'list', '--file-id', identity, '-n', '2', '--oneline'])
    assert summary.stdout.splitlines() == [f'{side[:12]}  asset.bin  side variant', f'{renamed[:12]}  renamed.bin  asset renamed']
    text = runner.invoke(app, ['leaf', 'list', '--file-id', identity])
    assert 'All branches: saved records' in text.stdout
    assert 'including unchanged content and renames' in text.stdout
    assert json_call('leaf', 'list', '--file-id', 'f' * 32) == []
    empty = runner.invoke(app, ['leaf', 'list', '--file-id', 'f' * 32])
    assert empty.exit_code == 0 and 'No saved records for file ID:' in empty.stdout
    assert runner.invoke(app, ['file', 'history', '--help']).exit_code != 0


@pytest.mark.parametrize('args', [
    ['asset.bin', '--file-id', 'f' * 32],
    ['--file-id', 'f' * 32, '--label', 'Approved'],
    ['--file-id', 'bad-id'],
    ['--file-id', 'F' * 32],
    ['--file-id', 'f' * 32, '--oneline', '--json'],
    ['--file-id', 'f' * 32, '-n', '0'],
])
def test_invalid_history_requests_leave_repository_and_worktree_unchanged(tmp_path, monkeypatch, args):
    repo, identity, *_ = history(tmp_path, monkeypatch)
    with repo.connect() as db:
        before = list(db.iterdump())
    files = {path.name: path.read_bytes() for path in repo.root.iterdir() if path.is_file()}
    result = run_command(app, ['leaf', 'list', *args])
    assert not result['ok']
    with repo.connect() as db:
        assert list(db.iterdump()) == before
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '1'
    assert {path.name: path.read_bytes() for path in repo.root.iterdir() if path.is_file()} == files
    assert repo.doctor().ok


def test_leaf_list_serve_alias_and_empty_project_contracts(tmp_path, monkeypatch):
    repo, identity, *_ = history(tmp_path, monkeypatch)
    for args in [[], ['asset.bin'], ['--label', 'Approved'], ['--file-id', identity]]:
        canonical = run_command(app, ['leaf', 'list', *args, '--json'])
        assert canonical['ok'] and canonical['result'] == json_call('leaf', 'list', *args)
        assert run_command(app, ['log', *args, '--json']) == canonical
    empty = Repository.init(tmp_path / 'empty')
    monkeypatch.chdir(empty.root)
    assert json_call('leaf', 'list') == []
    assert json_call('leaf', 'list', '--file-id', identity) == []
    help_result = runner.invoke(app, ['leaf', 'list', '--help'])
    assert help_result.exit_code == 0
    for term in ['current-branch', 'all-branch', 'unchanged', '--file-id', '--label']:
        assert term in help_result.stdout.lower()
