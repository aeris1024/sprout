import json

import pytest
from typer.testing import CliRunner

from sprout.cli import app
from sprout.errors import SproutError
from sprout.repository import Repository


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    file.write_bytes(b'first')
    repo.track([file])
    first = repo.commit('first').commit_id
    file.write_bytes(b'second')
    second = repo.commit('second').commit_id
    return repo, file, first, second


def state(repo, file):
    return (repo.head_position(), repo.buds(), repo.branches(), file.read_bytes(), repo.tracked())


@pytest.mark.parametrize('name,fragment', [
    ('main', 'branch already exists'),
    ('v1', 'name already used by tag'),
    ('has space', 'no whitespace'),
])
def test_refused_name_changes_nothing_even_with_unsaved_work(tmp_path, name, fragment):
    repo, file, first, _ = project(tmp_path)
    repo.create_tag('v1', first)
    file.write_bytes(b'unsaved')
    before = state(repo, file)
    with pytest.raises(SproutError, match=fragment):
        repo.grow_branch(name, start_point=first)
    assert state(repo, file) == before


def test_grows_a_branch_and_keeps_unsaved_work_as_a_bud(tmp_path):
    repo, file, first, second = project(tmp_path)
    file.write_bytes(b'unsaved')
    commit_id, bud = repo.grow_branch('rethink', '検討', start_point=first)
    assert commit_id == first
    head = repo.head_position()
    assert (head.branch, head.current_commit, head.at_branch_tip) == ('rethink', first, True)
    assert file.read_bytes() == b'first'
    assert bud.base_commit_id == second and bud.branch_name == 'main'
    assert repo.branch_references()[1].comment == '検討'
    assert repo.status() == []
    assert repo.doctor().ok


def test_grows_without_a_bud_when_nothing_is_unsaved(tmp_path):
    repo, file, first, _ = project(tmp_path)
    assert repo.grow_branch('rethink', start_point=first) == (first, None)
    assert repo.buds() == []


def test_failed_move_removes_the_branch_and_the_bud(tmp_path, monkeypatch):
    repo, file, first, _ = project(tmp_path)
    file.write_bytes(b'unsaved')
    before = state(repo, file)

    def fail(*args, **kwargs):
        raise OSError('disk failure')

    monkeypatch.setattr(repo, '_verify_manifest', fail)
    with pytest.raises(OSError):
        repo.grow_branch('rethink', start_point=first)
    monkeypatch.undo()
    assert state(repo, file) == before


def test_untracked_conflict_changes_nothing(tmp_path):
    repo, file, first, second = project(tmp_path)
    extra = repo.root / 'extra.bin'
    extra.write_bytes(b'tracked in second')
    repo.track([extra])
    third = repo.commit('third').commit_id
    repo.untrack([extra])
    file.write_bytes(b'unsaved')
    extra.write_bytes(b'now untracked')
    before = state(repo, file)
    with pytest.raises(SproutError) as error:
        repo.grow_branch('rethink', start_point=third)
    assert error.value.code == 'untracked_conflict'
    assert state(repo, file) == before


def test_before_first_commit_is_refused(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    with pytest.raises(SproutError, match='before first commit'):
        repo.grow_branch('rethink')


def test_cli_reports_the_kept_bud(tmp_path, monkeypatch):
    repo, file, first, _ = project(tmp_path)
    monkeypatch.chdir(repo.root)
    file.write_bytes(b'unsaved')
    result = CliRunner().invoke(app, ['branch', 'rethink', first, '--switch', '--keep-changes', '--json'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload['name'] == 'rethink' and payload['current'] is True
    assert payload['bud']['changes'] == [{'state': 'modified', 'path': 'asset.bin'}]


def test_cli_requires_switch_and_a_name(tmp_path, monkeypatch):
    repo, _, first, _ = project(tmp_path)
    monkeypatch.chdir(repo.root)
    for args in (['branch', 'rethink', '--keep-changes'], ['branch', '--keep-changes']):
        with pytest.raises(SproutError, match='--keep-changes requires'):
            CliRunner().invoke(app, args, catch_exceptions=False)
    assert 'rethink' not in {name for name, _commit, _comment in repo.branches()}
