import json
import pytest
from typer.testing import CliRunner
from sprout.cli import app
from sprout.repository import Repository
from sprout.errors import SproutError


def saved(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    a = repo.root / 'a.bin'
    a.write_bytes(b'same')
    repo.track([a])
    first = repo.commit('first').commit_id
    return repo, a, first


def test_move_copy_history_and_dedup(tmp_path, monkeypatch):
    repo, a, first = saved(tmp_path)
    monkeypatch.chdir(repo.root)
    identity = repo.manifest(first)['a.bin'].file_id
    b = repo.root / 'b.bin'
    repo.move(a, b)
    copy = repo.root / 'copy.bin'
    copy.write_bytes(b.read_bytes())
    repo.track([copy])
    second = repo.commit('moved and copied').commit_id
    assert repo.manifest(second)['b.bin'].file_id == identity
    assert repo.manifest(second)['copy.bin'].file_id != identity
    assert len(list(repo.objects.glob('*/*'))) == 1
    assert [r['path'] for r in repo.file_history(identity)] == ['b.bin', 'a.bin']
    result = CliRunner().invoke(app, ['leaf', 'list', '--file-id', identity, '--json'])
    assert result.exit_code == 0
    assert [r['path'] for r in json.loads(result.stdout)] == ['b.bin', 'a.bin']
    repo.restore(first)
    assert repo.tracked_ids() == {'a.bin': identity}
    repo.restore(second)
    assert repo.tracked_ids()['b.bin'] == identity
    repo.delete_commit(second)
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert repo.manifest(second)['b.bin'].file_id == identity


def test_reregistration_is_new_identity_and_committable(tmp_path):
    repo, a, first = saved(tmp_path)
    old = repo.tracked_ids()['a.bin']
    repo.untrack([a])
    repo.track([a])
    new = repo.tracked_ids()['a.bin']
    assert new != old
    assert repo.status() and repo._has_unsaved_changes()
    second = repo.commit('new material').commit_id
    assert repo.manifest(second)['a.bin'].file_id == new
    with pytest.raises(SproutError) as error:
        repo.restore(first, [a], discard=True)
    assert error.value.code == 'file_identity_conflict'
    repo.restore(first)
    assert repo.tracked_ids()['a.bin'] == old


def test_external_rename_and_same_path_overwrite(tmp_path, monkeypatch):
    repo, a, first = saved(tmp_path)
    old = repo.tracked_ids()['a.bin']
    a.write_bytes(b'atomic save replacement')
    second = repo.commit('edited').commit_id
    assert repo.manifest(second)['a.bin'].file_id == old
    renamed = repo.root / 'external.bin'
    a.rename(renamed)
    repo.track([renamed])
    third = repo.commit('external rename is new registration').commit_id
    assert repo.manifest(third)['external.bin'].file_id != old
    a.write_bytes(b'atomic save replacement')
    repo.track([a])
    assert repo.tracked_ids()['a.bin'] != old


def test_bud_and_branch_preserve_identity_and_partial_collision(tmp_path, monkeypatch):
    repo, a, first = saved(tmp_path)
    monkeypatch.chdir(repo.root)
    old = repo.tracked_ids()['a.bin']
    b = repo.root / 'b.bin'
    repo.move(a, b)
    bud = repo.save_bud()
    assert bud.files[0].file_id == old
    repo.restore(first, discard=True)
    repo.restore_bud(bud.id)
    assert repo.tracked_ids() == {'b.bin': old}
    second = repo.commit('renamed').commit_id
    before = b.read_bytes()
    with pytest.raises(SproutError) as error:
        repo.restore(first, [a], discard=True)
    assert error.value.code == 'file_identity_conflict'
    assert b.read_bytes() == before and not a.exists()
    repo.create_branch('past', start_point=first, switch=True)
    assert repo.tracked_ids() == {'a.bin': old}
    repo.switch('main')
    assert repo.tracked_ids() == {'b.bin': old}


def test_identity_roundtrip_in_archive_and_show(tmp_path, monkeypatch):
    repo, a, first = saved(tmp_path)
    monkeypatch.chdir(repo.root)
    identity = repo.tracked_ids()['a.bin']
    result = CliRunner().invoke(app, ['show', first, '--json'])
    assert json.loads(result.stdout)['files'][0]['file_id'] == identity
    output = tmp_path / 'archive'
    repo.archive(output)
    archive = json.loads((output / 'archive.json').read_text())
    assert archive['commits'][0]['files'][0]['file_id'] == identity
    assert repo.doctor().ok


def test_prune_protects_restored_material_identity_even_when_content_matches_tip(tmp_path):
    repo, a, first = saved(tmp_path)
    repo.untrack([a])
    repo.track([a])
    second = repo.commit('new identity with identical content').commit_id
    repo.untrack([a])
    a.unlink()
    repo.restore(first, [a])
    with pytest.raises(SproutError) as error:
        repo.prune(all_history=True)
    assert error.value.code == 'working_snapshot_would_be_pruned'
    assert repo.manifest(first)['a.bin'].file_id != repo.manifest(second)['a.bin'].file_id
