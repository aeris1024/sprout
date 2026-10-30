import pytest

from sprout.errors import SproutError
from sprout.repository import Repository


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    file.write_bytes(b'base')
    repo.track([file])
    repo.commit('base')
    return repo, file


def seqs(repo, table='commits'):
    with repo.connect() as db:
        return [row[0] for row in db.execute(f'SELECT seq FROM {table} ORDER BY seq')]


def test_deleted_commit_number_is_not_reused_and_recovery_succeeds(tmp_path):
    repo, file = project(tmp_path)
    repo.create_branch('side', switch=True)
    file.write_bytes(b'side')
    side = repo.commit('side tip').commit_id
    repo.switch('main')
    repo.delete_commit(side)
    file.write_bytes(b'main')
    repo.commit('main next')
    assert seqs(repo) == [1, 3]

    repo.restore_trash(repo.trash_items()[0]['id'])

    assert seqs(repo) == [1, 2, 3]
    with repo.connect() as db:
        order = [row[0] for row in db.execute('SELECT message FROM commits ORDER BY seq')]
    assert order == ['base', 'side tip', 'main next']
    assert repo.doctor().ok


def test_pruned_commit_number_is_not_reused(tmp_path):
    repo, file = project(tmp_path)
    repo.create_tag('start', 'main')
    file.write_bytes(b'middle')
    repo.commit('middle')
    file.write_bytes(b'end')
    repo.commit('end')
    repo.create_tag('end', 'main')
    file.write_bytes(b'tip')
    tip = repo.commit('tip').commit_id
    repo.delete_commit(tip)
    repo.prune('start', 'end')
    file.write_bytes(b'next')
    repo.commit('next')
    assert seqs(repo)[-1] == 5


def test_bud_and_trash_numbers_are_not_reused(tmp_path):
    repo, file = project(tmp_path)
    file.write_bytes(b'one')
    first = repo.save_bud()
    repo.restore('main', discard=True)
    repo.drop_bud(first.id)
    file.write_bytes(b'two')
    repo.save_bud()
    assert seqs(repo, 'buds') == [2]

    second = repo.commit('second').commit_id
    repo.delete_commit(second)
    first_item = repo.trash_items()[0]['id']
    repo.purge_trash(first_item)
    file.write_bytes(b'again')
    third = repo.commit('third').commit_id
    repo.delete_commit(third)
    assert seqs(repo, 'trash_entries') == [2]


def test_restore_conflict_reason_hides_sqlite_errors(tmp_path):
    repo, file = project(tmp_path)
    repo.create_branch('side', switch=True)
    file.write_bytes(b'side')
    side = repo.commit('side tip').commit_id
    repo.switch('main')
    repo.delete_commit(side)
    file.write_bytes(b'main')
    repo.commit('main next')
    item = repo.trash_items()[0]['id']
    with repo.connect() as db:
        # Force a uniqueness failure on restore through a colliding creation number.
        db.execute("UPDATE commits SET seq=2 WHERE message='main next'")

    with pytest.raises(SproutError) as error:
        repo.restore_trash(item)

    assert error.value.code == 'trash_restore_conflict'
    assert 'UNIQUE' not in str(error.value)
    assert 'constraint' not in str(error.value)


def test_doctor_reports_a_counter_behind_existing_numbers(tmp_path):
    repo, _file = project(tmp_path)
    assert repo.doctor().ok
    with repo.connect() as db:
        db.execute("UPDATE id_sequences SET last_value=0 WHERE name='commits'")

    assert [(issue.kind, issue.detail) for issue in repo.doctor().issues] == [('invalid_sequence', 'commits')]


def test_missing_counter_is_rejected_on_open(tmp_path):
    repo, _file = project(tmp_path)
    with repo.connect() as db:
        db.execute("DELETE FROM id_sequences WHERE name='buds'")

    with pytest.raises(SproutError) as error:
        Repository.discover(repo.root)

    assert error.value.details['reason'] == 'invalid_sequences'
