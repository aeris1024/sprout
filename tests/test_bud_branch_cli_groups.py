from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


runner = CliRunner()


def call(*args):
    result = run_command(app, [*args, '--json'])
    assert result['ok'], result
    return result['result']


def project(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repo.root)
    asset = repo.root / 'asset.bin'
    asset.write_bytes(b'base')
    repo.track([asset])
    leaf = repo.commit('base').commit_id
    return repo, asset, leaf


def test_bud_explicit_save_copy_names_clear_restore_and_pending_work(tmp_path, monkeypatch):
    repo, asset, _ = project(tmp_path, monkeypatch)
    asset.write_bytes(b'copied')
    saved = call('bud', 'save', '--keep-files', '--name', 'list')
    assert asset.read_bytes() == b'copied' and saved['name'] == 'list'
    assert call('bud', 'rename', saved['id'], 'create')['id'] == saved['id']
    assert call('bud', 'rename', saved['id'], '')['name'] == ''
    asset.write_bytes(b'other work')
    restored = call('bud', 'restore', saved['id'])
    assert restored['restored']['id'] == saved['id']
    assert restored['saved'] is not None and asset.read_bytes() == b'copied'
    assert saved['id'] not in {item['id'] for item in call('bud', 'list')}
    assert call('bud', 'list') == call('bud')
    pending = restored['saved']['id']
    call('bud', 'restore', pending)
    assert asset.read_bytes() == b'other work'
    result = call('bud', 'save', '--name', 'save')
    assert result['name'] == 'save' and asset.read_bytes() == b'base'


def test_bud_delete_confirmation_recovery_and_failures_preserve_work(tmp_path, monkeypatch):
    repo, asset, _ = project(tmp_path, monkeypatch)
    asset.write_bytes(b'draft')
    saved = call('bud', 'save', '--name', 'delete')
    before = call('bud', 'list')
    refused = run_command(app, ['bud', 'delete', saved['id'], '--json'])
    assert not refused['ok'] and call('bud', 'list') == before
    asset.write_bytes(b'working')
    refused = run_command(app, ['bud', 'restore', 'missing', '--json'])
    assert not refused['ok'] and asset.read_bytes() == b'working'
    assert call('bud', 'list') == before
    assert call('bud', 'delete', saved['id'], '--yes')['id'] == saved['id']
    assert call('bud', 'list') == []
    item = next(item for item in repo.trash_items() if item['kind'] == 'bud_delete')
    call('trash', 'restore', item['id'])
    assert call('bud', 'list')[0]['id'] == saved['id']
    assert asset.read_bytes() == b'working'


def test_branch_explicit_operations_handle_reserved_names_and_recovery(tmp_path, monkeypatch):
    repo, asset, leaf = project(tmp_path, monkeypatch)
    for name in ('list', 'create', 'rename', 'comment', 'delete'):
        result = call('branch', 'create', name, leaf, '-m', '  initial  ')
        assert result['name'] == name and result['commit_id'] == leaf
    original = next(item for item in call('branch', 'list') if item['name'] == 'list')
    assert call('branch', 'comment', 'list', ' revised ')['comment'] == 'revised'
    assert call('branch', 'comment', 'list', '')['comment'] == ''
    renamed = call('branch', 'rename', 'list', 'renamed')
    assert renamed['id'] == original['id']
    refused = run_command(app, ['branch', 'delete', 'main', '--json'])
    assert not refused['ok'] and repo.head_branch() == 'main'
    deleted = call('branch', 'delete', 'renamed')
    assert deleted['id'] == original['id']
    assert original['id'] in {item['id'] for item in call('branch', 'list', '--deleted')}
    call('trash', 'restore', next(item for item in repo.trash_items() if item['kind'] == 'branch_delete')['id'])
    assert original['id'] in {item['id'] for item in call('branch', 'list')}
    assert repo.resolve_commit(leaf) == leaf and asset.read_bytes() == b'base'


def test_branch_creation_keeps_current_switch_safety_until_move_integration(tmp_path, monkeypatch):
    repo, asset, leaf = project(tmp_path, monkeypatch)
    asset.write_bytes(b'draft')
    refused = run_command(app, ['branch', 'create', 'refused', leaf, '--switch', '--json'])
    assert not refused['ok'] and asset.read_bytes() == b'draft'
    assert 'refused' not in {name for name, _, _ in repo.branches()}
    created = call('branch', 'create', 'new-work', leaf, '--switch', '--keep-changes')
    assert created['current'] and created['bud'] is not None
    assert repo.head_branch() == 'new-work' and asset.read_bytes() == b'base'
    conflict = run_command(app, ['branch', 'rename', 'new-work', 'main', '--json'])
    assert not conflict['ok'] and repo.head_branch() == 'new-work'
    # The new hierarchy does not add a canonical branch switch operation.
    assert 'switch' not in runner.invoke(app, ['branch', '--help']).stdout


def test_transitional_legacy_bud_and_branch_flags_remain_available(tmp_path, monkeypatch):
    repo, asset, _ = project(tmp_path, monkeypatch)
    call('branch', 'old-name', '-m', 'legacy')
    assert call('branch', 'old-name', '--set-comment', 'edited')['comment'] == 'edited'
    assert any(item['name'] == 'old-name' for item in call('branch'))
    asset.write_bytes(b'draft')
    saved = call('bud', '--save', '--name', 'old-bud')
    assert call('bud', '--restore', saved['id'])['restored']['id'] == saved['id']
    assert asset.read_bytes() == b'draft'
