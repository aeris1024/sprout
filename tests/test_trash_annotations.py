import pytest

from sprout.errors import SproutError
from sprout.repository import Repository


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    file.write_bytes(b'saved')
    repo.track([file])
    return repo, file, repo.commit('base').commit_id


def only_item(repo, kind):
    items = repo.trash_items()
    assert [item['kind'] for item in items] == [kind]
    return items[0]


def rejected(repo, item, fragment):
    before = repo.trash_items()
    with pytest.raises(SproutError) as error:
        repo.restore_trash(item['id'])
    assert error.value.code == 'trash_restore_conflict'
    assert fragment in error.value.details['reason']
    assert 'constraint' not in str(error.value)
    assert repo.trash_items() == before


@pytest.mark.parametrize('remove', [
    lambda repo, commit: repo.set_note(commit, ''),
    lambda repo, commit: repo.set_note(commit, '   '),
])
def test_deleted_note_comes_back_with_content_and_time(tmp_path, remove):
    repo, _, commit = project(tmp_path)
    saved = repo.set_note(commit, '長いメモ\n二行目')
    remove(repo, commit)
    assert repo.annotations(commit).note is None

    item = only_item(repo, 'note_delete')
    assert item['title'] == '長いメモ' and item['target_id'] == commit
    assert repo.restore_trash(item['id'], dry_run=True)['dry_run']
    assert repo.annotations(commit).note is None
    repo.restore_trash(item['id'])

    restored = repo.annotations(commit)
    assert (restored.note, restored.note_updated_at) == ('長いメモ\n二行目', saved.note_updated_at)
    assert repo.trash_items() == []
    assert repo.doctor().ok


def test_clearing_an_empty_note_creates_no_item(tmp_path):
    repo, _, commit = project(tmp_path)
    repo.set_note(commit, '')
    assert repo.trash_items() == []


def test_note_recovery_does_not_overwrite_a_newer_note(tmp_path):
    repo, _, commit = project(tmp_path)
    repo.set_note(commit, 'old')
    repo.set_note(commit, '')
    item = only_item(repo, 'note_delete')
    repo.set_note(commit, 'new')
    rejected(repo, item, 'newer note')
    assert repo.annotations(commit).note == 'new'


def test_deleted_tag_comes_back_on_its_snapshot(tmp_path):
    repo, _, commit = project(tmp_path)
    repo.create_tag('v1', commit, '節目')
    created = repo.tags()[0]
    repo.delete_tag('v1')
    assert repo.tags() == []

    item = only_item(repo, 'tag_delete')
    assert (item['title'], item['target_id']) == ('v1', commit)
    repo.restore_trash(item['id'])
    assert repo.tags() == [created]
    assert repo.resolve_commit('v1') == commit


def test_unknown_tag_still_fails_and_records_nothing(tmp_path):
    repo, _, _ = project(tmp_path)
    with pytest.raises(SproutError, match='unknown tag'):
        repo.delete_tag('missing')
    assert repo.trash_items() == []


def test_deleted_branch_comes_back_with_tip_comment_and_id(tmp_path):
    repo, _, commit = project(tmp_path)
    repo.create_branch('side', '検討中')
    before = next(item for item in repo.branch_references() if item.name == 'side')
    repo.delete_branch('side')
    assert repo.deleted_branches()[0].name == 'side'

    item = only_item(repo, 'branch_delete')
    assert (item['title'], item['target_id']) == ('side', before.id)
    repo.restore_trash(item['id'])

    assert next(ref for ref in repo.branch_references() if ref.name == 'side') == before
    assert before.commit_id == commit
    assert repo.deleted_branches() == []
    assert repo.doctor().ok


@pytest.mark.parametrize('make_taken', [
    lambda repo: repo.create_branch('side'),
    lambda repo: repo.create_tag('side', 'main'),
])
def test_branch_recovery_refuses_a_name_in_use(tmp_path, make_taken):
    repo, _, _ = project(tmp_path)
    repo.create_branch('side')
    repo.delete_branch('side')
    item = only_item(repo, 'branch_delete')
    make_taken(repo)
    rejected(repo, item, 'already used')


@pytest.mark.parametrize('make_taken', [
    lambda repo: repo.create_branch('v1'),
    lambda repo: repo.create_tag('v1', 'main'),
])
def test_tag_recovery_refuses_a_name_in_use(tmp_path, make_taken):
    repo, _, commit = project(tmp_path)
    repo.create_tag('v1', commit)
    repo.delete_tag('v1')
    item = only_item(repo, 'tag_delete')
    make_taken(repo)
    rejected(repo, item, 'already used')


def gone_snapshot(tmp_path):
    repo, file, _ = project(tmp_path)
    file.write_bytes(b'next')
    return repo, repo.commit('next').commit_id


def remove_snapshot(repo, commit, kind):
    repo.delete_commit(commit)
    for item in repo.trash_items():
        if item['kind'] != kind:
            repo.purge_trash(item['id'])


@pytest.mark.parametrize('kind', ['note_delete', 'tag_delete', 'branch_delete'])
def test_recovery_needs_the_snapshot_it_belonged_to(tmp_path, kind):
    repo, commit = gone_snapshot(tmp_path)
    if kind == 'note_delete':
        repo.set_note(commit, 'note')
        repo.set_note(commit, '')
    elif kind == 'tag_delete':
        repo.create_tag('v1', commit)
        repo.delete_tag('v1')
    else:
        repo.create_branch('side', start_point=commit)
        repo.delete_branch('side')
    item = only_item(repo, kind)
    remove_snapshot(repo, commit, kind)
    rejected(repo, item, 'no longer exists')


def test_purging_a_deleted_branch_or_tag_needs_no_objects(tmp_path):
    repo, _, commit = project(tmp_path)
    repo.create_tag('v1', commit)
    repo.delete_tag('v1')
    item = only_item(repo, 'tag_delete')
    assert item['objects'] == [] and item['protected_bytes'] == 0
    repo.purge_trash(item['id'])
    assert repo.trash_items() == []
    assert repo.doctor().ok


def test_records_survive_reopening(tmp_path):
    repo, _, commit = project(tmp_path)
    repo.create_tag('v1', commit)
    repo.delete_tag('v1')
    reopened = Repository.discover(repo.root)
    reopened.restore_trash(only_item(reopened, 'tag_delete')['id'])
    assert reopened.resolve_commit('v1') == commit
