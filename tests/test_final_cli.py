"""The final public command surface and actual shell-completion protocols."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import run_command


CANONICAL = {'init', 'status', 'go', 'leaf', 'bud', 'branch', 'file', 'trash', 'maintenance', 'serve'}
ALIASES = {'commit', 'log', 'show', 'tree', 'diff', 'track', 'untrack', 'mv', 'switch', 'stash', 'tag'}
RETIRED = {'move', 'cover', 'file-history', 'message', 'thumbnail', 'note', 'label', 'preview',
           'restore', 'export', 'archive', 'cat', 'prune', 'delete-commit', 'gc', 'doctor', 'stats'}
runner = CliRunner()


def test_final_root_and_nested_command_surface_has_no_temporary_routes():
    root = get_command(app)
    assert set(root.commands) == CANONICAL | ALIASES
    assert {name for name, command in root.commands.items() if not command.hidden} == CANONICAL
    for path, expected in [
        (['leaf'], {'create', 'list', 'tree', 'show', 'edit', 'delete', 'prune', 'archive', 'tag', 'label', 'thumbnail', 'preview'}),
        (['leaf', 'preview'], {'list', 'add', 'replace', 'delete', 'export', 'order', 'edit', 'image'}),
        (['leaf', 'tag'], {'list', 'create', 'comment', 'delete'}),
        (['leaf', 'label'], {'list', 'add', 'remove'}),
        (['leaf', 'thumbnail'], {'show', 'set', 'delete', 'export', 'source'}),
        (['leaf', 'thumbnail', 'source'], {'show', 'set', 'clear', 'apply'}),
        (['file'], {'track', 'untrack', 'list', 'move', 'diff', 'restore', 'export', 'cat'}),
        (['bud'], {'save', 'list', 'restore', 'rename', 'delete'}),
        (['branch'], {'list', 'create', 'rename', 'comment', 'delete'}),
        (['trash'], {'list', 'show', 'restore', 'purge'}),
        (['maintenance'], {'stats', 'doctor', 'gc'}),
        (['stash'], {'push', 'list', 'pop', 'drop'}),
    ]:
        group = root
        for name in path:
            group = group.commands[name]
        assert set(group.commands) == expected
        assert runner.invoke(app, [*path, '--help']).exit_code == 0


@pytest.mark.parametrize('name', sorted(RETIRED))
def test_retired_root_commands_are_rejected_by_cli_and_serve(name):
    direct = runner.invoke(app, [name, '--help'])
    assert direct.exit_code == 2
    response = run_command(app, [name, '--json'])
    assert not response['ok'] and response['error']['code'] == 'usage_error'


@pytest.mark.parametrize('arguments', [
    ['branch', '_legacy'], ['bud', '_legacy'], ['branch', '--deleted'], ['bud', '--save'],
    ['trash', '--json'], ['tag', '--delete', 'name'], ['tag', 'name', '--set-comment', 'text'],
    ['branch', 'create', 'name', '--switch', '--keep-changes'],
    ['leaf', 'preview', 'metadata', 'main', 'id'],
    ['leaf', 'preview', 'edit', 'main', 'id', '--primary'],
    ['leaf', 'preview', 'edit', 'main', 'id', '--file-id', 'id'],
    ['leaf', 'preview', 'edit', 'main', 'id', '--clear-materials'],
])
def test_temporary_group_routes_and_removed_flags_are_not_public(arguments):
    response = run_command(app, arguments)
    assert not response['ok'] and response['error']['code'] == 'usage_error'


@pytest.fixture
def completion_project(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'completion-project')
    source = repo.root / 'asset.bin'
    source.write_bytes(b'base')
    repo.track([source]); repo.commit('base')
    repo.create_branch('sidework'); repo.create_tag('submitted')
    monkeypatch.chdir(repo.root)
    return repo


def complete(shell, args, incomplete=''):
    words = ['sprout', *args, incomplete]
    line = ' '.join(words)
    environment = {'_SPROUT_COMPLETE': f'complete_{shell}'}
    if shell == 'bash':
        environment.update(COMP_WORDS=line, COMP_CWORD=str(len(words) - 1))
    else:
        environment.update(_TYPER_COMPLETE_ARGS=line, _TYPER_COMPLETE_WORD_TO_COMPLETE=incomplete)
    result = runner.invoke(app, [], prog_name='sprout', env=environment)
    assert result.exit_code == 0, result.output
    if shell == 'powershell':
        return {item.split(':::')[0] for item in result.stdout.splitlines()}
    if shell == 'zsh':
        return set(re.findall(r'"([^"\n]+)"(?=:|\n|\))', result.stdout))
    return set(result.stdout.splitlines())


@pytest.mark.parametrize('shell', ['powershell', 'bash', 'zsh'])
def test_real_completion_protocols_cover_canonical_hierarchy_and_aliases(shell, completion_project):
    root = complete(shell, [])
    assert CANONICAL | ALIASES <= root
    assert not RETIRED & root
    assert {'status', 'stash'} <= complete(shell, [], 'sta')
    assert {'list', 'add', 'replace', 'edit', 'image'} <= complete(shell, ['leaf', 'preview'])
    assert {'push', 'list', 'pop', 'drop'} <= complete(shell, ['stash'])
    assert {'submitted'} <= complete(shell, ['leaf', 'show'], 'sub')
    assert {'submitted'} <= complete(shell, ['show'], 'sub')
    assert {'sidework'} <= complete(shell, ['go', '--branch'], 'side')
    assert {'sidework'} <= complete(shell, ['switch'], 'side')


def test_generated_bash_completion_parses_in_real_bash(tmp_path, monkeypatch):
    git_bash = Path('C:/Program Files/Git/bin/bash.exe')
    bash = str(git_bash) if git_bash.is_file() else shutil.which('bash')
    if not bash:
        pytest.skip('No Bash interpreter installed')
    # Ask Typer for a particular script instead of detecting the parent shell
    # of this test run (normally PowerShell on Windows).
    monkeypatch.setenv('_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION', '1')
    generated = runner.invoke(app, ['--show-completion', 'bash'], prog_name='sprout')
    assert generated.exit_code == 0
    script = tmp_path / 'sprout-completion.sh'
    script.write_bytes(generated.stdout.encode('utf-8'))
    result = subprocess.run([bash, '--noprofile', '--norc', '-n', str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_generated_powershell_completion_parses_in_real_powershell(tmp_path, monkeypatch):
    powershell = shutil.which('pwsh')
    if not powershell:
        pytest.skip('No PowerShell interpreter installed')
    monkeypatch.setenv('_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION', '1')
    generated = runner.invoke(app, ['--show-completion', 'powershell'], prog_name='sprout')
    assert generated.exit_code == 0
    script = tmp_path / 'sprout-completion.ps1'
    script.write_text(generated.stdout, encoding='utf-8')
    parser = tmp_path / 'parse.ps1'
    parser.write_text('param([string]$Target)\n$tokens=$null; $errors=$null\n'
                      '$null=[System.Management.Automation.Language.Parser]::ParseFile($Target,[ref]$tokens,[ref]$errors)\n'
                      'if($errors.Count){ $errors | Out-String | Write-Error; exit 1 }\n', encoding='utf-8')
    result = subprocess.run([powershell, '-NoProfile', '-File', str(parser), str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
