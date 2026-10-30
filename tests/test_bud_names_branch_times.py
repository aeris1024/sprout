import json
import sqlite3

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import TIMESTAMP_PATTERN, Repository


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    file.write_bytes(b'base')
    repo.track([file])
    repo.commit('base')
    return repo, file


def invoke(monkeypatch, repo, *args):
    monkeypatch.chdir(repo.root)
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_bud_name_is_saved_edited_and_cleared(tmp_path):
    repo, file = project(tmp_path)
    file.write_bytes(b'work')
    bud = repo.save_bud(' 配色の別案 ')
    assert bud.name == '配色の別案'
    assert repo.buds()[0].name == '配色の別案'
    assert repo.rename_bud(bud.id[:12], '新しい名前').name == '新しい名前'
    assert repo.rename_bud(bud.id, '').name == ''


def test_automatically_kept_bud_has_no_name(tmp_path):
    repo, file = project(tmp_path)
    first = repo.head_commit()
    file.write_bytes(b'next')
    repo.commit('next')
    file.write_bytes(b'work')
    assert repo.go(first).bud.name == ''


@pytest.mark.parametrize('name', ['a\nb', 'a\rb', 'x' * 257, 'a\x00b'])
def test_invalid_bud_names_are_rejected(tmp_path, name):
    repo, file = project(tmp_path)
    file.write_bytes(b'work')
    bud = repo.save_bud('ok')
    with pytest.raises(SproutError) as error:
        repo.rename_bud(bud.id, name)
    assert error.value.code == 'invalid_bud_name'
    assert repo.buds()[0].name == 'ok'
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute("UPDATE buds SET name=?", ('a\nb',))


def test_bud_name_through_the_cli(tmp_path, monkeypatch):
    repo, file = project(tmp_path)
    file.write_bytes(b'work')
    saved = json.loads(invoke(monkeypatch, repo, 'bud', '--save', '--name', '別案', '--json'))
    assert saved['name'] == '別案'
    assert '"別案"' in invoke(monkeypatch, repo, 'bud')
    renamed = json.loads(invoke(monkeypatch, repo, 'bud', '--rename', saved['id'], '改名', '--json'))
    assert renamed['name'] == '改名'
    tree = json.loads(invoke(monkeypatch, repo, 'tree', '--json'))
    assert tree['buds'][0]['name'] == '改名'


def test_bud_name_option_needs_save(tmp_path, monkeypatch):
    repo, _ = project(tmp_path)
    monkeypatch.chdir(repo.root)
    with pytest.raises(SproutError):
        CliRunner().invoke(app, ['bud', '--name', 'x'], catch_exceptions=False)


def test_branch_times_are_recorded_and_kept_on_rename(tmp_path, monkeypatch):
    repo, _ = project(tmp_path)
    main = repo.branch_references()[0]
    assert TIMESTAMP_PATTERN.fullmatch(main.created_at)
    repo.create_branch('side')
    side = next(item for item in repo.branch_references() if item.name == 'side')
    assert TIMESTAMP_PATTERN.fullmatch(side.created_at)
    repo.rename_branch('side', 'renamed')
    renamed = next(item for item in repo.branch_references() if item.name == 'renamed')
    assert renamed.created_at == side.created_at
    assert repo.deleted_branches() == []

    listed = json.loads(invoke(monkeypatch, repo, 'branch', '--json'))
    assert {item['name']: item['created_at'] for item in listed}['renamed'] == side.created_at

    repo.delete_branch('renamed')
    deleted = repo.deleted_branches()
    assert [item.name for item in deleted] == ['renamed']
    assert deleted[0].created_at == side.created_at
    assert TIMESTAMP_PATTERN.fullmatch(deleted[0].deleted_at)

    assert json.loads(invoke(monkeypatch, repo, 'branch', '--deleted', '--json'))[0]['deleted_at'] == deleted[0].deleted_at
    assert 'renamed' in invoke(monkeypatch, repo, 'branch', '--deleted')
    tree = json.loads(invoke(monkeypatch, repo, 'tree', '--json'))
    assert tree['deleted_branches'][0]['deleted_at'] == deleted[0].deleted_at
    assert 'created_at' in tree['branches'][0]


def test_branch_grown_automatically_has_a_creation_time(tmp_path):
    repo, file = project(tmp_path)
    first = repo.head_commit()
    file.write_bytes(b'next')
    repo.commit('next')
    repo.go(first)
    file.write_bytes(b'fork')
    result = repo.commit('fork')
    assert result.created_branch
    grown = next(item for item in repo.branch_references() if item.name == result.branch)
    assert TIMESTAMP_PATTERN.fullmatch(grown.created_at)


def test_database_keeps_deleted_time_consistent_with_deleted_flag(tmp_path):
    repo, _ = project(tmp_path)
    repo.create_branch('side')
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute("UPDATE branches SET deleted_at=created_at WHERE name='side'")
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute("UPDATE branches SET deleted=1, commit_id=NULL WHERE name='side'")


def test_deleted_commit_recovery_keeps_branch_times_and_bud_names(tmp_path):
    repo, file = project(tmp_path)
    file.write_bytes(b'next')
    tip = repo.commit('next').commit_id
    file.write_bytes(b'work')
    repo.save_bud('残す')
    before = repo.branch_references()[0].created_at
    repo.delete_commit(tip)
    repo.restore_trash(repo.trash_items()[0]['id'])
    assert repo.buds()[0].name == '残す'
    assert repo.branch_references()[0].created_at == before
    assert repo.doctor().ok
