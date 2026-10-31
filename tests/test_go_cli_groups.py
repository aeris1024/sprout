import pytest

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository, utc_timestamp
from sprout.serve import run_command


def call(*args):
    result = run_command(app, [*args, '--json'])
    assert result['ok'], result
    return result['result']


def project(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repo.root)
    asset = repo.root / 'asset.bin'
    asset.write_bytes(b'first')
    repo.track([asset])
    first = repo.commit('first').commit_id
    asset.write_bytes(b'second')
    second = repo.commit('second').commit_id
    repo.create_branch('side', start_point=second)
    return repo, asset, first, second


def state(repo, asset):
    return (repo.head_position(), repo.branches(), repo.buds(), repo.trash_items(),
            asset.read_bytes() if asset.exists() else None, repo.tracked_ids())


def test_go_selects_the_named_branch_even_when_tips_coincide(tmp_path, monkeypatch):
    repo, _, _, second = project(tmp_path, monkeypatch)
    result = call('go', 'side')
    assert (result['branch'], result['current_commit']) == ('side', second)
    result = call('go', '--branch', 'main')
    assert result['branch'] == 'main' and result['at_branch_tip']
    assert call('switch', 'side') == call('go', '--branch', 'side')
    assert repo.head_branch() == 'side'


def test_go_empty_branch_and_first_leaf_have_nullable_position(tmp_path, monkeypatch):
    repo, asset, _, second = project(tmp_path, monkeypatch)
    with repo.connect() as db:
        db.execute("INSERT INTO branches(id,name,commit_id,comment,created_at) VALUES(?,?,?,?,?)",
                   ('e' * 32, 'empty', None, '', utc_timestamp()))
    asset.write_bytes(b'draft')
    result = call('go', '--branch', 'empty')
    assert result['current_commit'] is None and result['at_branch_tip']
    assert result['bud']['base_commit_id'] == second and not asset.exists()
    asset.write_bytes(b'new start')
    repo.track([asset])
    created = call('leaf', 'create', '-m', 'empty branch first')
    assert created['branch'] == 'empty' and not created['created_branch']


def test_go_keep_branch_preserves_tip_and_mid_history_save_branches(tmp_path, monkeypatch):
    repo, asset, first, second = project(tmp_path, monkeypatch)
    repo.add_label(first, 'approved')
    result = call('go', first, '--keep-branch')
    assert result['branch'] == 'main' and not result['at_branch_tip']
    assert repo.head_commit() == second and asset.read_bytes() == b'first'
    asset.write_bytes(b'new line of work')
    created = call('leaf', 'create', '-m', 'fork')
    assert created['created_branch'] and created['branch'] != 'main'
    assert dict((name, leaf) for name, leaf, _ in repo.branches())['main'] == second
    assert repo.annotations(first).labels == ('approved',)


def test_go_default_reject_and_discard_policies_keep_work_recoverable(tmp_path, monkeypatch):
    repo, asset, first, second = project(tmp_path, monkeypatch)
    asset.write_bytes(b'draft')
    before = state(repo, asset)
    denied = run_command(app, ['go', first, '--reject-changes', '--json'])
    assert not denied['ok'] and denied['error']['code'] == 'uncommitted_changes'
    assert state(repo, asset) == before
    kept = call('go', first)
    assert kept['bud']['base_commit_id'] == second and asset.read_bytes() == b'first'
    asset.write_bytes(b'discarded work')
    discarded = call('go', second, '--discard')
    assert discarded['bud'] is None and asset.read_bytes() == b'second'
    item = next(item for item in repo.trash_items() if item['kind'] == 'discard')
    call('trash', 'restore', item['id'])
    # Recovery first creates a bud, preserving the current working files.
    assert asset.read_bytes() == b'second'
    latest = call('bud', 'list')[0]
    call('bud', 'restore', latest['id'])
    assert asset.read_bytes() == b'discarded work'


@pytest.mark.parametrize('flags', [[], ['--discard'], ['--reject-changes']])
def test_go_failed_materialization_leaves_all_state_unchanged(tmp_path, monkeypatch, flags):
    repo, asset, first, _ = project(tmp_path, monkeypatch)
    if '--reject-changes' not in flags:
        asset.write_bytes(b'draft')
    before = state(repo, asset)
    def fail(*args, **kwargs):
        raise OSError('injected disk failure')
    monkeypatch.setattr(repo, '_verify_manifest', fail)
    with pytest.raises(OSError, match='injected'):
        repo.go(first, reject_changes='--reject-changes' in flags, discard='--discard' in flags)
    assert state(repo, asset) == before


def test_go_invalid_flags_unknown_branch_and_untracked_conflict_change_nothing(tmp_path, monkeypatch):
    repo, asset, first, _ = project(tmp_path, monkeypatch)
    asset.write_bytes(b'draft')
    before = state(repo, asset)
    for args in [[], [first, '--branch', 'side'], ['--branch', 'side', '--keep-branch'],
                 [first, '--reject-changes', '--discard'], ['--branch', 'missing']]:
        result = run_command(app, ['go', *args, '--json'])
        assert not result['ok'] and state(repo, asset) == before
    extra = repo.root / 'extra.bin'
    extra.write_bytes(b'tracked')
    repo.track([extra])
    target = repo.commit('extra').commit_id
    repo.go(first)
    extra.write_bytes(b'untracked blocker')
    before = state(repo, asset)
    with pytest.raises(SproutError) as failure:
        repo.go(target)
    assert failure.value.code == 'untracked_conflict'
    assert state(repo, asset) == before and extra.read_bytes() == b'untracked blocker'


@pytest.mark.parametrize('policy', ['bud', 'reject', 'discard'])
@pytest.mark.parametrize('failure', [OSError, KeyboardInterrupt])
def test_branch_creation_failure_rolls_back_branch_and_work_recovery(tmp_path, monkeypatch, policy, failure):
    repo, asset, first, _ = project(tmp_path, monkeypatch)
    if policy != 'reject':
        asset.write_bytes(b'draft')
    before = state(repo, asset)
    def fail(*args, **kwargs):
        raise failure('injected disk failure')
    monkeypatch.setattr(repo, '_verify_manifest', fail)
    with pytest.raises(failure, match='injected'):
        repo.grow_branch('failed', start_point=first, reject_changes=policy == 'reject', discard=policy == 'discard')
    assert state(repo, asset) == before


def test_canonical_branch_switch_uses_go_policies_and_rolls_back_failed_creation(tmp_path, monkeypatch):
    repo, asset, first, _ = project(tmp_path, monkeypatch)
    asset.write_bytes(b'draft')
    before = state(repo, asset)
    refused = run_command(app, ['branch', 'create', 'denied', first, '--switch', '--reject-changes', '--json'])
    assert not refused['ok'] and state(repo, asset) == before
    invalid = run_command(app, ['branch', 'create', 'invalid', '--discard', '--json'])
    assert not invalid['ok'] and state(repo, asset) == before
    created = call('branch', 'create', 'rethink', first, '--switch')
    assert created['bud'] is not None and asset.read_bytes() == b'first'
    assert repo.head_branch() == 'rethink'
    asset.write_bytes(b'new draft')
    result = call('branch', 'create', 'discarding', first, '--switch', '--discard')
    assert result['bud'] is None and asset.read_bytes() == b'first'
    assert any(item['kind'] == 'discard' for item in repo.trash_items())
