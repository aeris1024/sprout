import os
from pathlib import Path

from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


runner = CliRunner()


def call(*args: str):
    result = run_command(app, [*args, '--json'])
    assert result['ok'], result
    return result['result']


def project(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repo.root)
    a = repo.root / 'a.bin'
    b = repo.root / 'b.bin'
    a.write_bytes(b'a1\x00\xff')
    b.write_bytes(b'b1')
    call('file', 'track', 'a.bin', 'b.bin')
    first = call('leaf', 'create', '-m', 'first')['id']
    return repo, a, b, first


def test_file_tracking_move_json_identity_and_collision(tmp_path, monkeypatch):
    repo, a, b, first = project(tmp_path, monkeypatch)
    identity = repo.tracked_ids()['a.bin']
    extra = repo.root / 'extra.bin'
    extra.write_bytes(b'extra')
    assert call('file', 'list') == {'tracked': ['a.bin', 'b.bin'], 'untracked': ['extra.bin']}
    assert call('file', 'list', '--tracked') == {'tracked': ['a.bin', 'b.bin']}
    assert call('file', 'list', '--untracked') == {'untracked': ['extra.bin']}
    moved = call('file', 'move', 'a.bin', 'nested/renamed.bin')
    assert moved == {'old_path': 'a.bin', 'new_path': 'nested/renamed.bin'}
    assert not a.exists() and repo.tracked_ids()['nested/renamed.bin'] == identity
    rejected = run_command(app, ['file', 'move', 'nested/renamed.bin', 'b.bin', '--json'])
    assert not rejected['ok'] and {'code', 'message', 'details'} <= rejected['error'].keys()
    assert b.read_bytes() == b'b1' and (repo.root / 'nested/renamed.bin').read_bytes() == b'a1\x00\xff'
    assert call('file', 'untrack', 'nested/renamed.bin')['paths'] == ['nested/renamed.bin']
    assert (repo.root / 'nested/renamed.bin').exists()
    assert repo.manifest(first)['a.bin'].file_id == identity


def test_file_paths_starting_with_options_and_required_arguments(tmp_path, monkeypatch):
    repo, _, _, _ = project(tmp_path, monkeypatch)
    path = repo.root / '--draft'
    path.write_bytes(b'draft')
    tracked = run_command(app, ['file', 'track', '--json', '--', '--draft'])
    assert tracked['ok'] and tracked['result']['paths'] == ['--draft']
    moved = run_command(app, ['file', 'move', '--json', '--', '--draft', '--renamed'])
    assert moved['ok'] and moved['result']['new_path'] == '--renamed'
    untracked = run_command(app, ['file', 'untrack', '--json', '--', '--renamed'])
    assert untracked['ok'] and (repo.root / '--renamed').exists()
    for args in [('track',), ('untrack',), ('restore', 'main'), ('history',), ('cover',)]:
        refused = run_command(app, ['file', *args, '--json'])
        assert not refused['ok'] and refused['error']['code'] == 'usage_error'


def test_file_diff_preserves_zero_one_and_two_leaf_comparisons(tmp_path, monkeypatch):
    repo, a, _, first = project(tmp_path, monkeypatch)
    a.write_bytes(b'a2')
    second = call('leaf', 'create', '-m', 'second')['id']
    a.write_bytes(b'a3')
    for refs in [(), (first,), (first, second)]:
        assert call('file', 'diff', *refs) == call('diff', *refs)
        assert call('file', 'diff', *refs)[0]['path'] == 'a.bin'
    assert repo.head_commit() == second and a.read_bytes() == b'a3'


def test_file_restore_is_partial_and_discard_keeps_recovery(tmp_path, monkeypatch):
    repo, a, b, first = project(tmp_path, monkeypatch)
    a.write_bytes(b'a2')
    b.write_bytes(b'b2')
    second = call('leaf', 'create', '-m', 'second')['id']
    a.write_bytes(b'unsaved a')
    b.write_bytes(b'unsaved b')
    before = repo.head_position()
    denied = run_command(app, ['file', 'restore', first, 'a.bin', '--json'])
    assert not denied['ok'] and a.read_bytes() == b'unsaved a'
    restored = call('file', 'restore', first, 'a.bin', '--discard')
    assert restored == {'commit_id': first, 'paths': ['a.bin']}
    assert a.read_bytes() == b'a1\x00\xff' and b.read_bytes() == b'unsaved b'
    assert repo.head_position() == before and repo.head_commit() == second
    assert any(item['kind'] == 'discard' for item in repo.trash_items())


def test_file_export_and_cat_keep_original_bytes_paths_times_and_force(tmp_path, monkeypatch):
    repo, a, b, _ = project(tmp_path, monkeypatch)
    # Store a known filesystem-representable time in a new leaf.
    stamp = 1_600_000_000_123_456_700
    os.utime(a, ns=(stamp, stamp))
    a.write_bytes(b'new bytes\x00\xff')
    os.utime(a, ns=(stamp, stamp))
    leaf = call('leaf', 'create', '-m', 'timestamp')['id']
    output = tmp_path / 'out'
    all_files = call('file', 'export', leaf, '--output', str(output))
    assert all_files['paths'] == ['a.bin', 'b.bin']
    assert (output / 'a.bin').read_bytes() == a.read_bytes()
    assert (output / 'a.bin').stat().st_mtime_ns == repo.manifest(leaf)['a.bin'].mtime_ns
    (output / 'a.bin').write_bytes(b'keep')
    refused = run_command(app, ['file', 'export', leaf, 'a.bin', '--output', str(output), '--json'])
    assert not refused['ok'] and (output / 'a.bin').read_bytes() == b'keep'
    assert call('file', 'export', leaf, 'a.bin', '--output', str(output), '--force')['paths'] == ['a.bin']
    cat = runner.invoke(app, ['file', 'cat', leaf, 'a.bin'])
    assert cat.exit_code == 0 and cat.stdout_bytes == a.read_bytes()
    assert repo.head_commit() == leaf and b.read_bytes() == b'b1'
