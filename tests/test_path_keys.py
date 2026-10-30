import os
import sqlite3
import unicodedata
from pathlib import Path

import pytest

from sprout.errors import SproutError
from sprout.repository import Repository, path_key, reject_path_conflicts


def project(tmp_path, name='Logo.png', content=b'v1'):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(content)
    repo.track([file])
    return repo, file, repo.commit('one').commit_id


def rename_outside(repo, old, new):
    os.rename(repo.root / old, repo.root / '.rename-step')
    (repo.root / new).parent.mkdir(parents=True, exist_ok=True)
    os.rename(repo.root / '.rename-step', repo.root / new)


def disk_names(repo):
    return sorted(
        path.relative_to(repo.root).as_posix()
        for path in repo.root.rglob('*')
        if path.is_file() and '.sprout' not in path.parts
    )


def file_ids(repo, commit):
    return {path: item.file_id for path, item in repo.manifest(commit).items()}


def test_path_key_ignores_case_and_composition():
    assert path_key('Logo.PNG') == path_key('logo.png')
    assert path_key(unicodedata.normalize('NFD', 'が.txt')) == path_key(unicodedata.normalize('NFC', 'が.txt'))
    assert path_key('a/b') != path_key('a/c')


@pytest.mark.parametrize('paths', [
    ['Logo.png', 'logo.png'],
    ['a', 'A/b'],
    [unicodedata.normalize('NFD', 'が.txt'), unicodedata.normalize('NFC', 'が.txt')],
])
def test_conflicting_paths_are_rejected(paths):
    with pytest.raises(SproutError) as error:
        reject_path_conflicts(paths)
    assert error.value.code == 'path_case_conflict'
    assert error.value.details['path'] in paths


SECOND_ID = 'b' * 32


def add_second_identity(repo):
    with repo.connect() as db:
        db.execute('INSERT INTO file_identities(id) VALUES(?)', (SECOND_ID,))


def test_database_rejects_a_second_path_with_the_same_key(tmp_path):
    repo, _, _ = project(tmp_path)
    add_second_identity(repo)
    with pytest.raises(sqlite3.IntegrityError, match='path_key'), repo.connect() as db:
        db.execute("INSERT INTO tracked_paths(path,path_key,file_id) VALUES('LOGO.png','logo.png',?)", (SECOND_ID,))


def test_commit_and_bud_rows_are_unique_by_key(tmp_path):
    repo, file, _ = project(tmp_path)
    add_second_identity(repo)
    with pytest.raises(sqlite3.IntegrityError, match='path_key'), repo.connect() as db:
        db.execute(
            "INSERT INTO commit_files(commit_id,path,path_key,object_hash,size,mtime_ns,file_id) "
            "SELECT commit_id,'LOGO.png',path_key,object_hash,size,mtime_ns,? FROM commit_files", (SECOND_ID,)
        )
    file.write_bytes(b'unsaved')
    repo.save_bud()
    with pytest.raises(sqlite3.IntegrityError, match='path_key'), repo.connect() as db:
        db.execute(
            "INSERT INTO bud_files(bud_id,path,path_key,object_hash,size,mtime_ns,file_id) "
            "SELECT bud_id,'LOGO.png',path_key,object_hash,size,mtime_ns,? FROM bud_files", (SECOND_ID,)
        )


def test_external_case_rename_is_reported_and_recorded_with_the_same_id(tmp_path):
    repo, _, one = project(tmp_path)
    original_id = file_ids(repo, one)['Logo.png']
    rename_outside(repo, 'Logo.png', 'logo.png')

    entries = repo.status()
    assert [(e.state, e.path, e.previous_path) for e in entries] == [('renamed', 'logo.png', 'Logo.png')]
    assert [(e.state, e.path, e.previous_path) for e in repo.diff()] == [('renamed', 'logo.png', 'Logo.png')]
    assert repo.tracked() == {'Logo.png'}, 'status must not write'

    two = repo.commit('renamed').commit_id

    assert file_ids(repo, two) == {'logo.png': original_id}
    assert repo.tracked() == {'logo.png'}
    assert repo.status() == []
    assert [(e.state, e.path, e.previous_path) for e in repo.diff(one, two)] == [('renamed', 'logo.png', 'Logo.png')]
    assert [row['path'] for row in repo.file_history(original_id)] == ['logo.png', 'Logo.png']


def test_case_rename_then_track_does_not_break_go_or_export(tmp_path):
    repo, _, one = project(tmp_path)
    rename_outside(repo, 'Logo.png', 'logo.png')
    assert repo.track([repo.root / 'logo.png']) == ['logo.png']
    assert repo.tracked() == {'logo.png'}
    (repo.root / 'logo.png').write_bytes(b'v2 precious')
    two = repo.commit('two').commit_id
    assert list(repo.manifest(two)) == ['logo.png']
    assert file_ids(repo, one)['Logo.png'] == file_ids(repo, two)['logo.png']

    repo.go(one)
    assert disk_names(repo) == ['Logo.png']
    assert (repo.root / 'Logo.png').read_bytes() == b'v1'
    assert repo.status() == []

    repo.go(two)
    assert disk_names(repo) == ['logo.png']
    assert (repo.root / 'logo.png').read_bytes() == b'v2 precious'
    assert repo.status() == []

    output = tmp_path / 'export'
    repo.export(two, output)
    assert (output / 'logo.png').read_bytes() == b'v2 precious'
    assert repo.doctor().ok


def test_move_changes_only_the_spelling_and_keeps_the_id(tmp_path, monkeypatch):
    repo, _, one = project(tmp_path)
    monkeypatch.chdir(repo.root)
    assert repo.move(Path('Logo.png'), Path('logo.png')) == ('Logo.png', 'logo.png')

    assert disk_names(repo) == ['logo.png']
    assert [(e.state, e.path) for e in repo.status()] == [('renamed', 'logo.png')]
    two = repo.commit('respelled').commit_id
    assert file_ids(repo, one)['Logo.png'] == file_ids(repo, two)['logo.png']


def test_move_to_a_path_differing_from_another_tracked_file_is_rejected(tmp_path, monkeypatch):
    repo, file, _ = project(tmp_path)
    other = repo.root / 'other.png'
    other.write_bytes(b'other')
    repo.track([other])
    monkeypatch.chdir(repo.root)
    with pytest.raises(SproutError):
        repo.move(Path('Logo.png'), Path('OTHER.png'))
    assert file.read_bytes() == b'v1' and other.read_bytes() == b'other'


def test_tracking_a_second_spelling_of_a_tracked_file_keeps_one_row(tmp_path):
    repo, _, one = project(tmp_path)
    repo.track([repo.root / 'LOGO.png'])
    assert len(repo.tracked()) == 1
    assert repo.status() == []
    assert repo.untracked_files() == []
    assert len(repo.manifest(one)) == 1


def test_folder_case_rename_round_trips(tmp_path):
    repo, _, one = project(tmp_path, 'Assets/a.png')
    rename_outside(repo, 'Assets', 'assets')
    assert [(e.state, e.path) for e in repo.status()] == [('renamed', 'assets/a.png')]
    two = repo.commit('folder renamed').commit_id
    assert list(repo.manifest(two)) == ['assets/a.png']

    repo.go(one)
    assert disk_names(repo) == ['Assets/a.png']
    assert repo.status() == []
    repo.go(two)
    assert disk_names(repo) == ['assets/a.png']
    assert repo.status() == []


def test_partial_restore_accepts_a_spelling_from_either_side(tmp_path):
    repo, file, one = project(tmp_path)
    rename_outside(repo, 'Logo.png', 'logo.png')
    (repo.root / 'logo.png').write_bytes(b'v2')
    repo.commit('two')
    repo.restore(one, [repo.root / 'logo.png'])
    assert (repo.root / 'Logo.png').read_bytes() == b'v1'
    assert repo.tracked() == {'Logo.png'}


def test_partial_restore_still_protects_unsaved_content_across_spelling(tmp_path):
    repo, _, one = project(tmp_path)
    rename_outside(repo, 'Logo.png', 'logo.png')
    (repo.root / 'logo.png').write_bytes(b'unsaved')
    with pytest.raises(SproutError) as error:
        repo.restore(one, [repo.root / 'logo.png'])
    assert error.value.code == 'uncommitted_changes'
    assert (repo.root / 'logo.png').read_bytes() == b'unsaved'


def test_bud_keeps_a_spelling_change(tmp_path):
    repo, _, one = project(tmp_path)
    rename_outside(repo, 'Logo.png', 'logo.png')
    bud = repo.save_bud()
    assert [(e.state, e.path, e.previous_path) for e in bud.changes] == [('renamed', 'logo.png', 'Logo.png')]
    repo.restore(one, discard=True)
    assert disk_names(repo) == ['Logo.png']
    repo.restore_bud(bud.id)
    assert disk_names(repo) == ['logo.png']


def test_nfd_path_is_tracked_once_and_kept_as_spelled(tmp_path):
    name = unicodedata.normalize('NFD', 'が.txt')
    repo, _, one = project(tmp_path, name)
    with repo.connect() as db:
        row = db.execute('SELECT path, path_key FROM commit_files').fetchone()
    assert row['path'] == name
    assert row['path_key'] == unicodedata.normalize('NFC', 'が.txt')
    assert list(repo.manifest(one)) == [name]


def test_deleted_commit_with_a_spelling_change_is_recoverable(tmp_path):
    repo, _, _one = project(tmp_path)
    rename_outside(repo, 'Logo.png', 'logo.png')
    two = repo.commit('two').commit_id
    repo.delete_commit(two)
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert list(repo.manifest(two)) == ['logo.png']
    assert repo.doctor().ok


def test_doctor_detects_wrong_keys_and_conflicts(tmp_path):
    repo, _, _ = project(tmp_path)
    assert repo.doctor().ok
    with repo.connect() as db:
        db.execute("UPDATE commit_files SET path_key='wrong'")
    assert ('invalid_path_key' in {issue.kind for issue in repo.doctor().issues})
    with repo.connect() as db:
        db.execute("UPDATE commit_files SET path_key='logo.png'")
        db.execute('INSERT INTO file_identities(id) VALUES(?)', (SECOND_ID,))
        db.execute(
            "INSERT INTO commit_files(commit_id,path,path_key,object_hash,size,mtime_ns,file_id) "
            "SELECT commit_id,'LOGO.png','other',object_hash,size,mtime_ns,? FROM commit_files", (SECOND_ID,)
        )
    assert 'path_conflict' in {issue.kind for issue in repo.doctor().issues}


@pytest.mark.skipif(os.name == 'nt', reason='Two spellings can only coexist on case-sensitive file systems')
def test_two_real_files_differing_by_case_are_rejected(tmp_path):
    repo, _, _ = project(tmp_path)
    (repo.root / 'logo.png').write_bytes(b'second')
    with pytest.raises(SproutError) as error:
        repo.track([repo.root / 'logo.png'])
    assert error.value.code == 'path_case_conflict'
    assert repo.tracked() == {'Logo.png'}
