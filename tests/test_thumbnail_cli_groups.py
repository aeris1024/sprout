"""Leaf thumbnails and project-wide automatic source have distinct canonical scopes."""
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


def call(*args):
    result = run_command(app, [*args, '--json'])
    assert result['ok'], result
    return result['result']


@pytest.fixture
def project(tmp_path, monkeypatch):
    repository = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repository.root)
    image = repository.root / 'poster.png'
    Image.new('RGB', (32, 24), 'green').save(image)
    repository.track([image])
    first = repository.commit('first').commit_id
    return repository, image, first


def test_source_identity_survives_moves_and_untracking(project):
    repository, image, _ = project
    selected = call('leaf', 'thumbnail', 'source', 'set', str(image))
    assert selected['path'] == 'poster.png' and selected['problem'] is None
    call('file', 'move', str(image), 'renamed.png')
    assert call('leaf', 'thumbnail', 'source', 'show') == {'file_id': selected['file_id'], 'path': 'renamed.png'}
    call('file', 'untrack', 'renamed.png')
    assert call('leaf', 'thumbnail', 'source', 'show') == {'file_id': selected['file_id'], 'path': None}
    assert call('leaf', 'thumbnail', 'source', 'clear') == {'file_id': None, 'path': None}
    assert repository.cover_file() == (None, None)


def test_source_apply_keeps_existing_and_manual_thumbnail_wins(project, tmp_path):
    repository, image, first = project
    call('leaf', 'thumbnail', 'source', 'set', str(image))
    Image.new('RGB', (32, 24), 'blue').save(image)
    second = call('leaf', 'create', '-m', 'automatic')['id']
    auto = repository.thumbnail(second)
    assert auto is not None
    plan = call('leaf', 'thumbnail', 'source', 'apply', '--dry-run')
    assert plan['applied'] == [first] and plan['kept'] == 1
    assert repository.thumbnail(first) is None
    assert call('leaf', 'thumbnail', 'source', 'apply')['applied'] == [first]
    assert repository.thumbnail(second) == auto
    external = tmp_path / 'outside.png'
    Image.new('RGB', (8, 8), 'red').save(external)
    Image.new('RGB', (32, 24), 'white').save(image)
    manual = call('leaf', 'create', '-m', 'manual', '--thumbnail', str(external))
    assert 'cover' not in manual
    assert repository.thumbnail(manual['id']).original_name == external.name


def test_individual_thumbnail_accepts_untracked_external_image_and_exports_safely(project, tmp_path):
    repository, image, first = project
    original = image.read_bytes()
    outside = tmp_path / 'outside.png'
    Image.new('RGB', (8, 8), 'red').save(outside)
    attachment = call('leaf', 'thumbnail', 'set', first, str(outside))
    assert call('leaf', 'thumbnail', 'show', first) == attachment
    output = tmp_path / 'export.png'
    assert call('leaf', 'thumbnail', 'export', first, '--output', str(output))['output'] == str(output)
    assert output.read_bytes() == outside.read_bytes()
    refused = run_command(app, ['leaf', 'thumbnail', 'export', first, '--output', str(output), '--json'])
    assert not refused['ok']
    call('leaf', 'thumbnail', 'export', first, '--output', str(output), '--force')
    assert not run_command(app, ['leaf', 'thumbnail', 'source', 'set', str(outside), '--json'])['ok']
    assert repository.cover_file() == (None, None)
    assert image.read_bytes() == original
    assert call('leaf', 'thumbnail', 'delete', first)['deleted']
    assert call('leaf', 'thumbnail', 'show', first) is None
    assert repository.manifest(first)['poster.png'].file_id == repository.tracked_ids()['poster.png']


def test_unreadable_source_does_not_fail_leaf_save_and_invalid_set_keeps_thumbnail(project):
    repository, image, first = project
    call('leaf', 'thumbnail', 'set', first, str(image))
    before = repository.thumbnail(first)
    invalid = repository.root / 'note.txt'
    invalid.write_text('not an image', encoding='utf8')
    call('file', 'track', str(invalid))
    assert not run_command(app, ['leaf', 'thumbnail', 'set', first, str(invalid), '--json'])['ok']
    assert repository.thumbnail(first) == before
    assert call('leaf', 'thumbnail', 'source', 'set', str(invalid))['problem'] == 'cover_not_image'
    saved = call('leaf', 'create', '-m', 'still saved')
    assert saved['cover'] == {'applied': False, 'reason': 'cover_not_image'}
    assert repository.thumbnail(saved['id']) is None


def test_thumbnail_help_distinguishes_leaf_target_and_project_source():
    runner = CliRunner()
    help_text = runner.invoke(app, ['leaf', 'thumbnail', '--help'])
    assert help_text.exit_code == 0
    for operation in ['show', 'set', 'delete', 'export', 'source']:
        assert operation in help_text.stdout
    assert runner.invoke(app, ['leaf', 'thumbnail', 'show']).exit_code != 0
    assert runner.invoke(app, ['leaf', 'thumbnail', 'source', 'show', '--help']).exit_code == 0
    assert runner.invoke(app, ['file', 'cover', '--help']).exit_code != 0
