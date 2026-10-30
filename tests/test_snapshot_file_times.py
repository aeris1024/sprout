import json
import os
import sqlite3
import sys

import pytest

from sprout import cli
from sprout.errors import SproutError
from sprout.repository import Repository


def stamp(path, ns):
    os.utime(path, ns=(ns, ns))
    return path.stat().st_mtime_ns  # Respect the source filesystem precision.


def history(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    a, b, marker = [repo.root / name for name in ('a.bin', 'b.bin', 'marker')]
    for file in (a, b):
        file.write_bytes(b'identical')
    marker.write_bytes(b'one')
    repo.track([a, b, marker])
    first_times = (stamp(a, 1_600_000_000_123_456_700), stamp(b, 1_650_000_000_765_432_100))
    first = repo.commit('first').commit_id
    second_times = (stamp(a, 1_700_000_000_111_222_300), stamp(b, 1_750_000_000_444_555_600))
    marker.write_bytes(b'two')
    second = repo.commit('second').commit_id
    return repo, a, b, marker, first, second, first_times, second_times


def times(a, b):
    return a.stat().st_mtime_ns, b.stat().st_mtime_ns


@pytest.mark.parametrize('operation', ['restore', 'partial', 'switch', 'go'])
def test_snapshot_times_across_materialization(tmp_path, operation):
    repo, a, b, marker, first, second, old, new = history(tmp_path)
    assert [repo.manifest(first)[p].mtime_ns for p in ('a.bin', 'b.bin')] == list(old)
    assert [repo.manifest(second)[p].mtime_ns for p in ('a.bin', 'b.bin')] == list(new)
    assert repo.manifest(first)['a.bin'].object_hash == repo.manifest(second)['b.bin'].object_hash
    # Timestamp differences alone must never block switching or restoring.
    stamp(a, new[0] + 10_000_000_000)
    assert repo.status() == []
    if operation == 'partial':
        repo.restore(first, [a])
        assert times(a, b) == (old[0], new[1])
        assert marker.read_bytes() == b'two'
        assert repo.current_commit() == second
    else:
        if operation == 'restore':
            repo.restore(first)
        elif operation == 'switch':
            repo.create_branch('past', start_point=first)
            repo.switch('past')
        else:
            assert repo.go(first).bud is None
        assert times(a, b) == old
        assert marker.read_bytes() == b'one'
    assert repo.status() == []
    assert Repository.discover(repo.root).doctor().ok
    with repo.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM objects').fetchone()[0] == 3


def test_timestamp_only_change_policy_and_later_capture(tmp_path):
    repo, a, b, marker, first, second, old, new = history(tmp_path)
    changed = stamp(a, new[0] + 20_000_000_000)
    assert repo.status() == []
    assert repo.diff() == []
    assert {entry.path for entry in repo.diff(first, second)} == {'marker'}
    assert [row['id'] for row in repo.log(a)] == [first]
    with pytest.raises(SproutError, match='nothing to commit'):
        repo.commit('timestamp only')
    with pytest.raises(SproutError, match='no unsaved changes'):
        repo.save_bud()
    marker.write_bytes(b'three')
    third = repo.commit('captures every path').commit_id
    assert repo.manifest(third)['a.bin'].mtime_ns == changed
    assert repo.manifest(second)['a.bin'].mtime_ns == new[0]


def test_export_archive_and_json_use_snapshot_times(tmp_path, monkeypatch, capsys):
    repo, a, b, marker, first, second, old, new = history(tmp_path)
    for commit, expected in ((first, old), (second, new)):
        output = tmp_path / commit
        repo.export(commit, output)
        assert times(output / a.name, output / b.name) == expected
        monkeypatch.chdir(repo.root)
        monkeypatch.setattr(sys, 'argv', ['sprout', 'show', commit, '--json'])
        assert cli.main() == 0
        files = {f['path']: f for f in json.loads(capsys.readouterr().out)['files']}
        assert (files[a.name]['mtime_ns'], files[b.name]['mtime_ns']) == expected
    archive = tmp_path / 'archive'
    repo.archive(archive)
    model = json.loads((archive / 'archive.json').read_text(encoding='utf-8'))
    for commit in model['commits']:
        files = {f['path']: archive / f['archive_path'] for f in commit['files']}
        assert times(files[a.name], files[b.name]) == (old if commit['id'] == first else new)


def test_bud_retains_individual_times(tmp_path):
    repo, a, b, marker, first, second, old, new = history(tmp_path)
    draft = stamp(a, new[0] + 30_000_000_000)
    marker.write_bytes(b'draft')
    bud = repo.save_bud()
    repo.restore(first, discard=True)
    repo.restore_bud(bud.id)
    assert times(a, b) == (draft, new[1])
    assert marker.read_bytes() == b'draft'


@pytest.mark.parametrize('interrupted', [False, True])
def test_failed_restore_recovers_original_per_path_times(tmp_path, monkeypatch, interrupted):
    repo, a, b, marker, first, second, old, new = history(tmp_path)
    apply = repo._apply_restore_action
    failure = KeyboardInterrupt if interrupted else OSError
    def fail(directory, action):
        apply(directory, action)
        if action['kind'] == 'install':
            raise failure('stop after first installation')
    with monkeypatch.context() as context:
        context.setattr(repo, '_apply_restore_action', fail)
        with pytest.raises(failure):
            repo.restore(first)
    reopened = Repository.discover(repo.root)
    assert times(a, b) == new
    assert marker.read_bytes() == b'two'
    assert reopened.current_commit() == second
    reopened.restore(first)
    assert times(a, b) == old


@pytest.mark.parametrize('value', [None, 'bad', 1.5])
def test_invalid_snapshot_times_rejected_and_diagnosed(tmp_path, value):
    repo, a, b, marker, first, second, old, new = history(tmp_path)
    with pytest.raises(sqlite3.IntegrityError), repo.connect() as db:
        db.execute('UPDATE commit_files SET mtime_ns=?', (value,))
    # NULL is prevented by NOT NULL even when CHECK constraints are disabled.
    if value is None:
        return
    # Simulate external corruption that bypasses CHECK constraints.
    with repo.connect() as db:
        db.execute('PRAGMA ignore_check_constraints=ON')
        db.execute('UPDATE commit_files SET mtime_ns=? WHERE commit_id=?', (value, first))
    assert 'invalid_file_time' in {issue.kind for issue in repo.doctor().issues}
    with pytest.raises(SproutError) as error:
        repo.manifest(first)
    assert error.value.code == 'invalid_file_time'
    with pytest.raises(SproutError, match='invalid saved file time'):
        repo.archive(tmp_path / 'bad-archive')


@pytest.mark.parametrize('ns', [0, -1_000_000_000, 1_700_000_000_000_000_000])
def test_epoch_and_coarse_times_survive_archive_and_restore(tmp_path, ns):
    repo = Repository.init(tmp_path / 'project')
    asset = repo.root / 'asset.bin'
    asset.write_bytes(b'asset')
    try:
        actual = stamp(asset, ns)
    except (OSError, OverflowError):
        pytest.skip('filesystem cannot represent requested time')
    repo.track([asset])
    first = repo.commit('time').commit_id
    stamp(asset, actual + 2_000_000_000)
    assert repo.status() == []
    repo.restore(first)
    assert asset.stat().st_mtime_ns == actual
    archive = tmp_path / 'archive'
    repo.archive(archive)
    files = json.loads((archive / 'archive.json').read_text())['commits'][0]['files']
    assert (archive / files[0]['archive_path']).stat().st_mtime_ns == actual
