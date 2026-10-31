"""Canonical CLI entry points during the staged command migration."""
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


runner = CliRunner()


def call(*args: str) -> dict:
    result = run_command(app, [*args, '--json'])
    assert result['ok'], result
    return result['result']


def project(tmp_path: Path, monkeypatch):
    root = tmp_path / 'project'
    assert runner.invoke(app, ['init', str(root)]).exit_code == 0
    asset = root / 'asset.bin'
    asset.write_bytes(b'first')
    monkeypatch.chdir(root)
    assert call('track', 'asset.bin') == {'paths': ['asset.bin']}
    return Repository.discover(root), asset


def test_leaf_groups_expose_only_the_operations_ready_to_use():
    root = runner.invoke(app, ['--help'])
    assert root.exit_code == 0
    for group in ('leaf', 'file', 'maintenance', 'bud', 'branch', 'trash'):
        assert group in root.stdout
    leaf = runner.invoke(app, ['leaf', '--help'])
    assert leaf.exit_code == 0
    for command in ('create', 'tree', 'show', 'delete', 'prune', 'archive'):
        assert command in leaf.stdout
    for deferred in ('restore', 'note', 'history', 'cover'):
        assert runner.invoke(app, ['leaf', deferred, '--help']).exit_code != 0
    for group in ('file', 'maintenance'):
        assert runner.invoke(app, [group, '--help']).exit_code == 0


def test_leaf_workflow_keeps_old_json_options_thumbnail_and_v1(tmp_path, monkeypatch):
    repo, asset = project(tmp_path, monkeypatch)
    with repo.connect() as db:
        schema = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
    assert schema == '1'
    image = tmp_path / 'outside.png'
    Image.new('RGB', (16, 12), 'navy').save(image)

    result = call('leaf', 'create', '-m', 'first', '--thumbnail', str(image))
    leaf = result['id']
    assert result['message'] == 'first' and result['branch'] == 'main'
    assert set(result) == {'id', 'message', 'branch', 'branch_id', 'created_branch', 'removed_paths'}
    assert call('leaf', 'show', leaf) == call('show', leaf)
    assert call('leaf', 'tree') == call('tree')
    assert call('leaf', 'show', leaf)['thumbnail']['original_name'] == image.name
    with repo.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == schema
    assert asset.read_bytes() == b'first'

    asset.write_bytes(b'second')
    old = call('commit', '-m', 'second')
    assert call('leaf', 'show', old['id'])['message'] == 'second'


def test_leaf_archive_dry_run_and_write_preserve_the_source(tmp_path, monkeypatch):
    repo, asset = project(tmp_path, monkeypatch)
    leaf = call('leaf', 'create', '-m', 'first')['id']
    output = tmp_path / 'archive'
    args = ('--output', str(output), '--dry-run')
    dry = call('leaf', 'archive', *args)
    assert dry == call('archive', *args)
    assert dry['commits'] == 1 and dry['files'] > 0
    assert not output.exists()
    actual = call('leaf', 'archive', '--output', str(output))
    assert actual['dry_run'] is False and (output / 'index.html').is_file()
    assert repo.head_commit() == leaf and asset.read_bytes() == b'first'
    refused = run_command(app, ['leaf', 'archive', '--output', str(repo.root), '--json'])
    assert refused['ok'] is False
    assert asset.read_bytes() == b'first'


def test_leaf_delete_retains_confirmation_references_and_trash_recovery(tmp_path, monkeypatch):
    repo, asset = project(tmp_path, monkeypatch)
    first = call('leaf', 'create', '-m', 'first')['id']
    asset.write_bytes(b'second')
    second = call('leaf', 'create', '-m', 'second')['id']
    assert not run_command(app, ['leaf', 'delete', second, '--json'])['ok']
    assert repo.head_commit() == second
    dry = call('leaf', 'delete', second, '--dry-run')
    assert dry == call('delete-commit', second, '--dry-run')
    assert repo.trash_items() == []

    call('leaf', 'delete', second, '--yes')
    assert repo.head_commit() == first and asset.read_bytes() == b'second'
    trash = repo.trash_items()
    assert len(trash) == 1
    call('trash', 'restore', trash[0]['id'])
    assert repo.resolve_commit(second) == second
    assert asset.read_bytes() == b'second'


def test_leaf_delete_refuses_tagged_leaf_without_changing_data(tmp_path, monkeypatch):
    repo, asset = project(tmp_path, monkeypatch)
    leaf = call('leaf', 'create', '-m', 'first')['id']
    repo.create_tag('keep')
    refused = run_command(app, ['leaf', 'delete', leaf, '--yes', '--json'])
    assert refused['ok'] is False and refused['error']['code'] == 'tagged_commit'
    assert repo.head_commit() == leaf and repo.trash_items() == []
    assert asset.read_bytes() == b'first'


def test_leaf_prune_keeps_boundaries_working_files_and_irreversible_contract(tmp_path, monkeypatch):
    repo, asset = project(tmp_path, monkeypatch)
    first = call('leaf', 'create', '-m', 'first')['id']
    repo.create_tag('start')
    asset.write_bytes(b'middle')
    middle = call('leaf', 'create', '-m', 'middle')['id']
    asset.write_bytes(b'last')
    last = call('leaf', 'create', '-m', 'last')['id']
    repo.create_tag('end')
    asset.write_bytes(b'draft')
    rejected = run_command(app, ['leaf', 'prune', 'start', 'end', '--json'])
    assert not rejected['ok'] and 'irreversible' in rejected['error']['message']
    conflict = run_command(app, ['leaf', 'prune', 'start', 'end', '--all', '--dry-run', '--json'])
    assert not conflict['ok']
    dry = call('leaf', 'prune', 'start', 'end', '--dry-run')
    assert dry == call('prune', 'start', 'end', '--dry-run')
    assert [item['id'] for item in dry['removed_commits']] == [middle]
    assert call('leaf', 'prune', '--all', '--dry-run')['mode'] == 'all'
    assert repo.resolve_commit(middle) == middle
    call('leaf', 'prune', 'start', 'end', '--yes')
    assert {entry['id'] for entry in call('leaf', 'tree')['commits']} == {first, last}
    assert repo.head_commit() == last and repo.trash_items() == []
    assert asset.read_bytes() == b'draft'


def test_nested_leaf_usage_errors_keep_serve_usable(tmp_path, monkeypatch):
    repo, _ = project(tmp_path, monkeypatch)
    missing = run_command(app, ['leaf', 'create', '--json'])
    assert missing['ok'] is False and missing['error']['code'] == 'usage_error'
    assert repo.head_commit() is None
    assert call('leaf', 'tree')['commits'] == []
    created = call('leaf', 'create', '-m', 'after usage error')
    assert call('leaf', 'show', created['id'])['message'] == 'after usage error'
