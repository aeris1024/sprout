import json

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    file.write_bytes(b'saved')
    repo.track([file])
    return repo, file, repo.commit('base').commit_id


def item_of(repo, kind):
    items = [item for item in repo.trash_items() if item['kind'] == kind]
    assert len(items) == 1
    return items[0]


def bud_contents(repo, bud):
    output = repo.root.parent / f'bud-{bud.id[:8]}.bin'
    item = next(state for state in bud.files if state.path == 'asset.bin')
    with output.open('wb') as target:
        repo._copy_verified_object(item, target)
    return output.read_bytes()


def test_dropped_bud_goes_to_trash_and_comes_back_with_name_and_ids(tmp_path):
    repo, file, _ = project(tmp_path)
    file.write_bytes(b'bud work')
    bud = repo.save_bud('別案')
    repo.restore('main', discard=True)
    repo.purge_trash(item_of(repo, 'discard')['id'])

    repo.drop_bud(bud.id)
    assert repo.buds() == []
    item = item_of(repo, 'bud_delete')
    assert item['title'] == '別案' and item['target_id'] == bud.id
    assert item['objects']
    repo.gc()
    working = file.read_bytes(), file.stat().st_mtime_ns

    assert repo.restore_trash(item['id'], dry_run=True)['dry_run']
    assert repo.buds() == []
    repo.restore_trash(item['id'])

    restored = repo.buds()[0]
    assert (restored.id, restored.name, restored.files) == (bud.id, '別案', bud.files)
    assert bud_contents(repo, restored) == b'bud work'
    assert (file.read_bytes(), file.stat().st_mtime_ns) == working
    assert repo.trash_items() == []
    assert repo.doctor().ok


@pytest.mark.parametrize('action', ['restore', 'switch'])
def test_discard_keeps_replaced_work_in_trash(tmp_path, action):
    repo, file, base = project(tmp_path)
    file.write_bytes(b'precious')
    if action == 'restore':
        repo.restore(base, discard=True)
    else:
        repo.switch('main', discard=True)
    assert file.read_bytes() == b'saved'
    assert repo.status() == []
    assert repo.buds() == []

    item = item_of(repo, 'discard')
    assert item['title'] == 'asset.bin'
    repo.gc()
    repo.restore_trash(item['id'])
    assert file.read_bytes() == b'saved', 'recovery must not change working files'
    bud = repo.buds()[0]
    assert bud_contents(repo, bud) == b'precious'
    repo.restore_bud(bud.id)
    assert file.read_bytes() == b'precious'


def test_partial_discard_keeps_work_and_only_touches_selected_files(tmp_path):
    repo, file, base = project(tmp_path)
    other = repo.root / 'other.bin'
    other.write_bytes(b'other saved')
    repo.track([other])
    repo.commit('second')
    file.write_bytes(b'precious')
    other.write_bytes(b'other unsaved')
    repo.restore('main', [file], discard=True)
    assert file.read_bytes() == b'saved'
    assert other.read_bytes() == b'other unsaved'
    assert item_of(repo, 'discard')['title'] == 'asset.bin +1'


@pytest.mark.parametrize('action', ['restore', 'switch'])
def test_discard_without_changes_creates_no_item(tmp_path, action):
    repo, _, base = project(tmp_path)
    if action == 'restore':
        repo.restore(base, discard=True)
    else:
        repo.switch('main', discard=True)
    assert repo.trash_items() == []


def test_discard_that_fails_leaves_no_item_and_keeps_work(tmp_path, monkeypatch):
    repo, file, base = project(tmp_path)
    file.write_bytes(b'precious')

    def fail(*args, **kwargs):
        raise OSError('disk failure')

    monkeypatch.setattr(repo, '_verify_manifest', fail)
    with pytest.raises(OSError):
        repo.restore(base, discard=True)
    monkeypatch.undo()
    assert file.read_bytes() == b'precious'
    assert repo.trash_items() == []
    assert repo.buds() == []


def test_recovering_a_bud_whose_base_is_gone_is_rejected(tmp_path):
    repo, file, _ = project(tmp_path)
    file.write_bytes(b'next')
    tip = repo.commit('next').commit_id
    file.write_bytes(b'work')
    bud = repo.save_bud()
    repo.drop_bud(bud.id)
    repo.restore('main', discard=True)
    repo.delete_commit(tip)
    commit_item = item_of(repo, 'commit')
    repo.purge_trash(commit_item['id'])

    item = item_of(repo, 'bud_delete')
    with pytest.raises(SproutError) as error:
        repo.restore_trash(item['id'])
    assert error.value.code == 'trash_restore_conflict'
    assert 'no longer exists' in error.value.details['reason']
    assert item_of(repo, 'bud_delete')['id'] == item['id']
    assert repo.buds() == []


def test_purged_work_is_reclaimed_by_gc(tmp_path):
    repo, file, _ = project(tmp_path)
    file.write_bytes(b'only here')
    repo.drop_bud(repo.save_bud().id)
    item = item_of(repo, 'bud_delete')
    assert repo.gc(dry_run=True).removed_objects == 0, 'trash protects the content'
    repo.purge_trash(item['id'])
    repo.restore('main', discard=True)
    repo.purge_trash(item_of(repo, 'discard')['id'])
    assert repo.gc().removed_objects == 1
    assert repo.doctor().ok


def test_cli_reports_recovery_and_json_shape(tmp_path, monkeypatch):
    repo, file, _ = project(tmp_path)
    monkeypatch.chdir(repo.root)
    file.write_bytes(b'work')
    runner = CliRunner()
    bud_id = json.loads(runner.invoke(app, ['bud', 'save', '--json']).stdout)['id']
    dropped = runner.invoke(app, ['bud', 'delete', bud_id, '--yes'])
    assert 'sprout trash' in dropped.stdout
    listed = json.loads(runner.invoke(app, ['trash', 'list', '--json']).stdout)
    assert listed[0]['kind'] == 'bud_delete'
    detail = json.loads(runner.invoke(app, ['trash', 'show', listed[0]['id'], '--json']).stdout)
    assert {change['table'] for change in detail['changes']} == {'buds', 'bud_files'}
