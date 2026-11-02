"""External API v1 contracts, snapshot isolation, and real process output."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

from PIL import Image
import pytest
from typer.testing import CliRunner

from sprout import __version__, cli
from sprout.repository import Repository


runner = CliRunner()


def call(command):
    result = runner.invoke(cli.app, [command, '--json'])
    assert result.exit_code == 0, result.output
    assert result.stderr == ''
    return json.loads(result.stdout)


def save(repo, message):
    file = repo.root / '資料 file.txt'
    file.write_text(message, encoding='utf-8')
    repo.track([file])
    return repo.commit(message).commit_id


def utc(value):
    assert datetime.fromisoformat(value).utcoffset() == timedelta(0)


def test_identity_empty_subdirectory_move_and_distinct_repository(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / '日本語 project')
    monkeypatch.chdir(repo.root)
    info = call('info')
    assert set(info) == {'api_version', 'sprout_version', 'repository', 'capabilities'}
    assert type(info['api_version']) is int and info['api_version'] == 1
    assert info['sprout_version'] == __version__
    assert info['capabilities'] == ['info.json.v1', 'catalog.json.v1']
    assert set(info['repository']) == {'id', 'root', 'created_at'}
    utc(info['repository']['created_at'])
    import uuid
    uuid.UUID(info['repository']['id'])
    assert call('catalog') == {'api_version': 1, 'repository': info['repository'], 'variants': []}
    sub = repo.root / 'sub'; sub.mkdir()
    monkeypatch.chdir(sub)
    assert call('info') == info
    assert call('catalog')['repository'] == info['repository']
    monkeypatch.chdir(tmp_path)
    moved = tmp_path / '移動 renamed'; repo.root.rename(moved)
    monkeypatch.chdir(moved)
    expected = {**info['repository'], 'root': str(moved)}
    assert call('info')['repository'] == expected
    assert call('catalog')['repository'] == expected
    assert Repository.init(tmp_path / 'other').repository_info()['id'] != expected['id']
    assert 'Capabilities:' in runner.invoke(cli.app, ['info']).stdout
    assert runner.invoke(cli.app, ['catalog']).stdout == 'No tagged variants.\n'


def test_scope_order_nulls_updates_and_tag_retargeting(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project'); monkeypatch.chdir(repo.root)
    first = save(repo, '最初 空白 AbC')
    repo.add_label(first, 'OnlyLabel')
    assert call('catalog')['variants'] == []
    repo.create_tag('zTag', first)
    repo.create_tag('ATag', first, comment='日本語 comment')
    repo.create_branch('side', start_point=first, switch=True)
    side = save(repo, '別ブランチ')
    repo.create_tag('sideTag', side)
    repo.switch('main'); repo.delete_branch('side')
    untagged = save(repo, 'タグなし先端'); repo.add_label(untagged, 'Excluded')
    with repo.connect() as db:
        db.execute("UPDATE commits SET created_at='2026-01-01T00:00:00.000000+00:00'")
    variants = call('catalog')['variants']
    assert [v['commit_id'] for v in variants] == sorted([first, side])
    with repo.connect() as db:
        db.execute("UPDATE commits SET created_at='2026-01-02T00:00:00.000000+00:00' WHERE id=?", (side,))
    assert [v['commit_id'] for v in call('catalog')['variants']] == [side, first]
    item = next(v for v in variants if v['commit_id'] == first)
    assert set(item) == {'commit_id', 'created_at', 'message', 'tags', 'note', 'note_updated_at', 'labels', 'thumbnail'}
    assert item['message'] == '最初 空白 AbC'
    assert item['note'] is item['note_updated_at'] is item['thumbnail'] is None
    assert [t['name'] for t in item['tags']] == ['ATag', 'zTag']
    assert all(set(t) == {'name', 'comment', 'created_at'} for t in item['tags'])
    assert item['tags'][0]['comment'] == '日本語 comment'
    repo.set_note(first, 'メモ 空白 AbC'); repo.add_label(first, 'abc'); repo.add_label(first, 'Abc')
    image = tmp_path / '日本語 preview.png'; Image.new('RGB', (8, 6), 'red').save(image)
    attachment = repo.set_thumbnail(first, image)
    item = next(v for v in call('catalog')['variants'] if v['commit_id'] == first)
    assert item['note'] == 'メモ 空白 AbC'
    assert item['labels'] == ['Abc', 'OnlyLabel', 'abc']
    assert item['tags'][1]['comment'] == ''  # Existing storage uses an empty comment.
    assert item['thumbnail']['object_hash'] == attachment.object_hash
    assert item['thumbnail']['commit_id'] == first
    assert item['thumbnail']['size'] == image.stat().st_size
    for value in [item['created_at'], item['note_updated_at'], item['thumbnail']['created_at'], item['thumbnail']['updated_at'], *[t['created_at'] for t in item['tags']]]:
        utc(value)
    Image.new('RGB', (8, 6), 'blue').save(image); replacement = repo.set_thumbnail(first, image)
    assert replacement.object_hash != attachment.object_hash
    assert next(v for v in call('catalog')['variants'] if v['commit_id'] == first)['thumbnail']['object_hash'] == replacement.object_hash
    repo.delete_thumbnail(first); repo.set_note(first, ''); repo.remove_label(first, 'abc')
    cleared = next(v for v in call('catalog')['variants'] if v['commit_id'] == first)
    assert cleared['note'] is cleared['note_updated_at'] is cleared['thumbnail'] is None
    assert cleared['labels'] == ['Abc', 'OnlyLabel']
    repo.delete_tag('ATag'); repo.delete_tag('zTag'); repo.create_tag('zTag', untagged)
    variants = call('catalog')['variants']
    assert {v['commit_id'] for v in variants} == {side, untagged}
    assert all(v['note'] is v['note_updated_at'] is v['thumbnail'] is None for v in variants)
    repo.delete_tag('zTag'); repo.delete_tag('sideTag')
    assert call('catalog')['variants'] == []


def test_catalog_snapshot_survives_concurrent_metadata_update(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    commit = save(repo, 'first'); repo.create_tag('before', commit); repo.set_note(commit, 'before')
    image = tmp_path / 'before.png'; Image.new('RGB', (8, 6), 'red').save(image)
    repo.set_thumbnail(commit, image)
    original = Repository._annotations_many_from_db
    def update_during_read(db, ids):
        # A separate WAL writer commits after repository/tags/commits were read.
        with repo.connect() as writer:
            writer.execute("UPDATE tags SET name='after'")
            writer.execute("UPDATE commit_notes SET note='after'")
            writer.execute("UPDATE commit_attachments SET original_name='after.png'")
            writer.execute("INSERT INTO commit_labels(commit_id,label) VALUES (?, 'after')", (commit,))
        return original(db, ids)
    with monkeypatch.context() as patch:
        patch.setattr(repo, '_annotations_many_from_db', update_during_read)
        snapshot = repo.catalog()['variants'][0]
    assert snapshot['tags'][0]['name'] == snapshot['note'] == 'before'
    assert snapshot['labels'] == []
    assert snapshot['thumbnail']['original_name'] == 'before.png'
    current = repo.catalog()['variants'][0]
    assert current['tags'][0]['name'] == current['note'] == 'after'
    assert current['labels'] == ['after']
    assert current['thumbnail']['original_name'] == 'after.png'


@pytest.mark.parametrize('command', ['info', 'catalog'])
def test_existing_discovery_recovers_interrupted_operation(tmp_path, monkeypatch, command):
    repo = Repository.init(tmp_path / 'project'); monkeypatch.chdir(repo.root)
    operation = repo.tmp / 'restore-test'; operation.mkdir()
    (operation / 'plan.json').write_text(json.dumps({'version': 1, 'actions': [], 'attempted': 0, 'rollback': None}))
    repo._set_active_operation(operation.name)
    assert call(command)['repository']['id'] == repo.repository_info()['id']
    assert not operation.exists()
    with repo.connect() as db:
        assert db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()[0] == ''


@pytest.mark.parametrize('command', ['info', 'catalog'])
def test_database_exclusive_lock_is_not_an_empty_success(tmp_path, monkeypatch, capsys, command):
    repo = Repository.init(tmp_path / 'project'); monkeypatch.chdir(repo.root)
    with sqlite3.connect(repo.db_path) as writer:
        writer.execute('PRAGMA journal_mode=DELETE')
        writer.execute('BEGIN EXCLUSIVE')
        monkeypatch.setattr(sys, 'argv', ['sprout', command, '--json'])
        assert cli.main() == 1
        output = capsys.readouterr()
        assert output.out == ''
        assert 'locked' in json.loads(output.err)['message']


def test_metadata_reads_do_not_read_objects_or_change_state(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project'); monkeypatch.chdir(repo.root)
    commit = save(repo, 'saved'); repo.create_tag('kept', commit)
    (repo.root / '資料 file.txt').write_bytes(b'unsaved')
    def forbidden(*args, **kwargs):
        pytest.fail('catalog must not load file manifests, decode images, or expand objects')
    monkeypatch.setattr(Repository, '_manifest_from_db', forbidden)
    monkeypatch.setattr(Repository, 'commit_graph', forbidden)
    monkeypatch.setattr(Repository, '_read_object', forbidden)
    monkeypatch.setattr(Image, 'open', forbidden)
    with repo.connect() as db:
        before = list(db.iterdump())
    files = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in repo.root.iterdir() if p.is_file()}
    with repo.lock():
        assert call('info')['repository'] == call('catalog')['repository']
    with repo.connect() as db:
        assert list(db.iterdump()) == before
    assert files == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in repo.root.iterdir() if p.is_file()}
    assert commit in runner.invoke(cli.app, ['catalog']).stdout


@pytest.mark.parametrize('command', ['info', 'catalog'])
@pytest.mark.parametrize('problem', ['missing', 'schema', 'corrupt', 'recovery', 'locked'])
def test_structured_failures(tmp_path, monkeypatch, capsys, command, problem):
    project = tmp_path / 'project'; project.mkdir()
    db_lock = None
    if problem != 'missing':
        repo = Repository.init(project)
        if problem == 'schema':
            with repo.connect() as db:
                db.execute("UPDATE meta SET value='999' WHERE key='schema_version'")
        elif problem == 'corrupt':
            repo.db_path.write_bytes(b'broken database')
        elif problem in ('recovery', 'locked'):
            repo._set_active_operation('restore-test')
            if problem == 'locked':
                # Valid plan reaches the existing repository-lock check.
                operation = repo.tmp / 'restore-test'; operation.mkdir()
                (operation / 'plan.json').write_text(json.dumps({'version': 1, 'actions': [], 'attempted': 0, 'rollback': None}))
                db_lock = repo.lock(); db_lock.__enter__()
    monkeypatch.chdir(project)
    monkeypatch.setattr(sys, 'argv', ['sprout', command, '--json'])
    try:
        assert cli.main() != 0
        output = capsys.readouterr()
        assert output.out == ''
        error = json.loads(output.err)
        assert set(error) == {'code', 'message', 'details'}
        if problem == 'missing':
            assert error['code'] == 'not_initialized'
            assert not (project / '.sprout').exists()
        if problem == 'locked':
            assert error['code'] == 'repository_locked'
    finally:
        if db_lock:
            db_lock.__exit__(None, None, None)


@pytest.mark.parametrize('command', ['info', 'catalog'])
def test_real_executable_utf8_and_output_channels(tmp_path, command):
    executable = Path(sys.executable).with_name('sprout.exe')
    if os.name != 'nt' or not executable.exists():
        executable_args = [sys.executable, '-m', 'sprout']
    else:
        executable_args = [str(executable)]
    repo = Repository.init(tmp_path / '日本語 project')
    commit = save(repo, '日本語 空白 🌱'); repo.create_tag('Tag日本語', commit)
    env = {**os.environ, 'PYTHONIOENCODING': 'cp932'}
    process = subprocess.run([*executable_args, command, '--json'], cwd=repo.root, env=env, capture_output=True)
    assert process.returncode == 0 and process.stderr == b''
    result = json.loads(process.stdout.decode('utf-8'))
    assert result['repository']['root'] == str(repo.root)
    if command == 'catalog':
        assert result['variants'][0]['message'] == '日本語 空白 🌱'
    failed = subprocess.run([*executable_args, command, '--json'], cwd=tmp_path, env=env, capture_output=True)
    assert failed.returncode != 0 and failed.stdout == b''
    assert json.loads(failed.stderr.decode('utf-8'))['code'] == 'not_initialized'


def test_reproducible_real_cli_integration(tmp_path):
    executable = Path(sys.executable).with_name('sprout.exe' if os.name == 'nt' else 'sprout')
    if not executable.is_file():
        pytest.skip('Install the Sprout console entry point to run executable integration')
    script = Path(__file__).parents[1] / 'scripts' / 'verify_catalog_api.py'
    process = subprocess.run([sys.executable, str(script), '--executable', str(executable), '--output', str(tmp_path)],
                             capture_output=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=120)
    assert process.returncode == 0, process.stderr
    report = json.loads(Path(process.stdout.strip()).read_text(encoding='utf-8'))
    assert report['variants'] == 3 and report['state_unchanged']
    assert report['image_formats'] == ['JPEG', 'PNG', 'WEBP']
