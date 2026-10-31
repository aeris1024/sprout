from PIL import Image
from typer.main import get_command
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


runner = CliRunner()


def call(*args):
    result = run_command(app, [*args, '--json'])
    assert result['ok'], result
    return result['result']


def project(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repo.root)
    asset = repo.root / 'asset.bin'
    asset.write_bytes(b'first')
    call('track', 'asset.bin')
    thumbnail = tmp_path / 'image.png'
    Image.new('RGB', (16, 16), 'navy').save(thumbnail)
    leaf = call('commit', '-m', 'first', '--thumbnail', str(thumbnail))['id']
    return repo, asset, leaf


def test_alias_read_operations_match_canonical_json_and_creation_options(tmp_path, monkeypatch):
    repo, asset, first = project(tmp_path, monkeypatch)
    assert call('show', first) == call('leaf', 'show', first)
    assert call('show', first)['thumbnail']['original_name'] == 'image.png'
    assert call('tree') == call('leaf', 'tree')
    assert call('log') == call('leaf', 'list')
    assert call('log', 'asset.bin', '-n', '1') == call('leaf', 'list', 'asset.bin', '-n', '1')
    identity = repo.tracked_ids()['asset.bin']
    assert call('log', '--file-id', identity) == call('leaf', 'list', '--file-id', identity)
    asset.write_bytes(b'second')
    second = call('leaf', 'create', '-m', 'second')['id']
    asset.write_bytes(b'draft')
    for refs in [(), (first,), (first, second)]:
        assert call('diff', *refs) == call('file', 'diff', *refs)


def test_track_untrack_and_mv_keep_paths_identity_and_rejection_contract(tmp_path, monkeypatch):
    repo, asset, _ = project(tmp_path, monkeypatch)
    identity = repo.tracked_ids()['asset.bin']
    assert call('mv', 'asset.bin', 'renamed.bin') == {'old_path': 'asset.bin', 'new_path': 'renamed.bin'}
    assert repo.tracked_ids()['renamed.bin'] == identity
    (repo.root / 'occupied').write_bytes(b'keep')
    alias_error = run_command(app, ['mv', 'renamed.bin', 'occupied', '--json'])
    canonical_error = run_command(app, ['file', 'move', 'renamed.bin', 'occupied', '--json'])
    assert alias_error == canonical_error and not alias_error['ok']
    assert call('untrack', 'renamed.bin') == {'paths': ['renamed.bin']}
    assert (repo.root / 'renamed.bin').read_bytes() == b'first'
    assert call('track', 'renamed.bin') == {'paths': ['renamed.bin']}


def test_switch_alias_selects_explicit_branch_and_has_go_safety(tmp_path, monkeypatch):
    repo, asset, _ = project(tmp_path, monkeypatch)
    call('branch', 'create', 'side')
    assert call('switch', 'side') == call('go', '--branch', 'side')
    asset.write_bytes(b'draft')
    alias_error = run_command(app, ['switch', 'main', '--reject-changes', '--json'])
    canonical_error = run_command(app, ['go', '--branch', 'main', '--reject-changes', '--json'])
    assert alias_error == canonical_error and not alias_error['ok']
    moved = call('switch', 'main')
    assert moved['bud'] is not None and repo.head_branch() == 'main'


def test_stash_aliases_preserve_options_explicit_pop_consumption_and_drop_confirmation(tmp_path, monkeypatch):
    repo, asset, _ = project(tmp_path, monkeypatch)
    asset.write_bytes(b'draft')
    saved = call('stash', 'push', '--keep-files', '--name', 'work')
    assert saved['name'] == 'work' and asset.read_bytes() == b'draft'
    assert call('stash', 'list') == call('bud', 'list')
    asset.write_bytes(b'other work')
    restored = call('stash', 'pop', saved['id'])
    assert restored['restored']['id'] == saved['id'] and restored['saved'] is not None
    assert asset.read_bytes() == b'draft'
    assert saved['id'] not in {item['id'] for item in call('stash', 'list')}
    remaining = call('stash', 'list')[0]['id']
    alias_error = run_command(app, ['stash', 'drop', remaining, '--json'])
    canonical_error = run_command(app, ['bud', 'delete', remaining, '--json'])
    assert alias_error == canonical_error and not alias_error['ok']
    assert call('stash', 'drop', remaining, '--yes')['id'] == remaining
    assert call('stash', 'list') == [] and asset.read_bytes() == b'draft'
    moved = call('stash', 'push', '--name', 'moved')
    assert moved['name'] == 'moved' and asset.read_bytes() == b'first'
    for args in [('pop',), ('apply', moved['id'])]:
        error = run_command(app, ['stash', *args, '--json'])
        assert not error['ok'] and error['exit_code'] == 2


def test_tag_alias_lists_or_creates_literal_command_word_names(tmp_path, monkeypatch):
    _, _, first = project(tmp_path, monkeypatch)
    assert call('tag') == call('leaf', 'tag', 'list') == []
    for name in ['list', 'create', 'delete', 'comment']:
        created = call('tag', name, first, '-m', '  initial  ')
        assert created['name'] == name and created['comment'] == 'initial'
    assert call('tag') == call('leaf', 'tag', 'list')
    alias_error = run_command(app, ['tag', 'list', '--json'])
    canonical_error = run_command(app, ['leaf', 'tag', 'create', 'list', '--json'])
    assert alias_error == canonical_error and not alias_error['ok']


def test_help_lists_ten_canonical_entries_and_all_fifteen_alias_patterns():
    command = get_command(app)
    canonical = {'init', 'status', 'go', 'leaf', 'bud', 'branch', 'file', 'trash', 'maintenance', 'serve'}
    assert {name for name, child in command.commands.items() if not child.hidden} == canonical
    normal = runner.invoke(app, ['--help'])
    assert normal.exit_code == 0 and '--help-aliases' in normal.stdout
    aliases = runner.invoke(app, ['--help-aliases'])
    assert aliases.exit_code == 0
    assert aliases.stdout.count(' -> ') == 15
    assert 'stash pop BUD' in aliases.stdout and 'consumes it on success' in aliases.stdout
    assert 'no staging area' in aliases.stdout and 'no stash apply' in aliases.stdout


def test_hidden_aliases_complete_but_temporary_legacy_entries_do_not():
    command = get_command(app)
    context = command.make_context('sprout', [], resilient_parsing=True)
    completions = {item.value for item in command.shell_complete(context, '')}
    aliases = {'commit', 'log', 'show', 'tree', 'diff', 'track', 'untrack', 'mv', 'switch', 'stash', 'tag'}
    assert aliases <= completions
    assert 'move' not in completions and 'restore' not in completions and 'preview' not in completions
    assert {item.value for item in command.shell_complete(context, 'sta')} >= {'stash', 'status'}
    stash = command.commands['stash']
    stash_context = stash.make_context('stash', [], parent=context, resilient_parsing=True)
    assert {'push', 'list', 'pop', 'drop'} <= {item.value for item in stash.shell_complete(stash_context, '')}
