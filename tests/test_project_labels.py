"""Project label candidates come from live leaves rather than a persistent dictionary."""
import io
import json

import pytest
from typer.testing import CliRunner

from sprout import __version__
from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command, serve


def project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    asset = repo.root / 'asset.bin'
    asset.write_bytes(b'first')
    repo.track([asset])
    return repo, asset, repo.commit('first').commit_id


def call(*args):
    response = run_command(app, [*args, '--json'])
    assert response['ok'], response
    return response['result']


def test_project_labels_are_empty_and_read_only_without_schema_changes(tmp_path):
    repo, asset, first = project(tmp_path)
    assert repo.project_labels() == []
    repo.add_label(first, 'Keep')
    with repo.connect() as db:
        before = list(db.iterdump())
        assert db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == '1'
    work = asset.read_bytes(), asset.stat().st_mtime_ns
    assert repo.project_labels() == [{'name': 'Keep', 'leaf_count': 1}]
    with repo.connect() as db:
        assert list(db.iterdump()) == before
    assert (asset.read_bytes(), asset.stat().st_mtime_ns) == work


def test_project_labels_count_all_branches_and_deleted_branch_leaves(tmp_path):
    repo, asset, first = project(tmp_path)
    repo.add_label(first, '  Cafe\u0301  ')
    repo.add_label(first, 'Café')
    repo.add_label(first, 'Draft')
    repo.add_label(first, 'draft')
    repo.create_branch('side', switch=True)
    asset.write_bytes(b'side')
    side = repo.commit('side').commit_id
    repo.add_label(side, 'Café')
    repo.add_label(side, 'Only side')
    repo.go('main')
    expected = [{'name': 'Café', 'leaf_count': 2}, {'name': 'Draft', 'leaf_count': 1},
                {'name': 'Only side', 'leaf_count': 1}, {'name': 'draft', 'leaf_count': 1}]
    assert repo.project_labels() == expected
    repo.delete_branch('side')
    assert repo.project_labels() == expected
    other = Repository.init(tmp_path / 'other')
    assert other.project_labels() == []
    foreign = other.root / 'foreign.bin'
    foreign.write_bytes(b'other')
    other.track([foreign])
    other.add_label(other.commit('other project').commit_id, 'Foreign only')
    assert repo.project_labels() == expected


def test_project_labels_follow_leaf_deletion_and_recovery(tmp_path):
    repo, asset, first = project(tmp_path)
    asset.write_bytes(b'second')
    second = repo.commit('second').commit_id
    repo.add_label(first, 'shared')
    repo.add_label(second, 'shared')
    repo.add_label(second, 'only deleted')
    repo.delete_commit(second)
    assert repo.project_labels() == [{'name': 'shared', 'leaf_count': 1}]
    item = next(item for item in repo.trash_items() if item['kind'] == 'commit')
    repo.restore_trash(item['id'])
    assert repo.project_labels() == [{'name': 'only deleted', 'leaf_count': 1}, {'name': 'shared', 'leaf_count': 2}]
    repo.remove_label(second, 'only deleted')
    repo.remove_label(second, 'shared')
    repo.remove_label(first, 'shared')
    assert repo.project_labels() == []


def test_canonical_label_commands_share_existing_annotations_and_filter(tmp_path, monkeypatch):
    repo, _, first = project(tmp_path)
    monkeypatch.chdir(repo.root)
    assert call('leaf', 'label', 'list') == []
    annotations = call('leaf', 'label', 'add', first, '  Cafe\u0301  ')
    assert annotations['labels'] == ['Café']
    assert call('leaf', 'label', 'list') == [{'name': 'Café', 'leaf_count': 1}]
    assert call('leaf', 'label', 'list', first) == annotations
    assert call('label', first) == annotations  # Transitional caller until the final migration.
    assert [row['id'] for row in call('log', '--label', 'Café')] == [first]
    runner = CliRunner()
    text = runner.invoke(app, ['leaf', 'label', 'list'])
    assert text.exit_code == 0 and 'Café\t1 leaves' in text.stdout
    help_text = runner.invoke(app, ['leaf', 'label', 'list', '--help'])
    assert help_text.exit_code == 0 and 'omit' in help_text.stdout
    assert call('leaf', 'label', 'remove', first, 'Café')['labels'] == []
    assert call('leaf', 'label', 'list') == []
    assert 'No labels' in runner.invoke(app, ['leaf', 'label', 'list']).stdout


@pytest.mark.parametrize('invalid,code', [('', 'empty_label'), ('x' * 65, 'label_too_long')])
def test_canonical_label_commands_preserve_input_constraints(tmp_path, monkeypatch, invalid, code):
    repo, _, first = project(tmp_path)
    monkeypatch.chdir(repo.root)
    response = run_command(app, ['leaf', 'label', 'add', first, invalid, '--json'])
    assert not response['ok'] and response['error']['code'] == code
    assert repo.project_labels() == []


def test_label_candidates_work_over_json_lines_serve(tmp_path, monkeypatch):
    repo, _, first = project(tmp_path)
    monkeypatch.chdir(repo.root)
    source = io.StringIO('\n'.join(json.dumps({'id': index, 'args': [*args, '--json']}) for index, args in enumerate([
        ['leaf', 'label', 'add', first, 'submitted'], ['leaf', 'label', 'list'],
        ['leaf', 'label', 'list', first], ['leaf', 'label', 'remove', first, 'submitted'],
        ['leaf', 'label', 'list'],
    ])))
    sink = io.StringIO()
    serve(app, __version__, source, sink)
    responses = [json.loads(line) for line in sink.getvalue().splitlines()][1:]
    assert all(response['ok'] and response['exit_code'] == 0 for response in responses)
    assert responses[1]['result'] == [{'name': 'submitted', 'leaf_count': 1}]
    assert responses[2]['result']['labels'] == ['submitted']
    assert responses[4]['result'] == []
