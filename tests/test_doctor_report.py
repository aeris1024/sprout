import json

from typer.testing import CliRunner

from sprout.cli import app
from sprout.repository import Repository


def broken_project(tmp_path):
    repo = Repository.init(tmp_path / 'project')
    file = repo.root / 'asset.bin'
    file.write_bytes(b'content')
    repo.track([file])
    commit = repo.commit('base').commit_id
    digest = repo.manifest(commit)['asset.bin'].object_hash
    (repo.objects / digest[:2] / digest).write_bytes(b'corrupt')
    return repo, digest


def test_report_returns_found_issues_successfully(tmp_path, monkeypatch):
    repo, digest = broken_project(tmp_path)
    monkeypatch.chdir(repo.root)
    runner = CliRunner()

    plain = runner.invoke(app, ['doctor', '--json'])
    assert plain.exit_code == 1

    report = runner.invoke(app, ['doctor', '--report', '--json'])
    assert report.exit_code == 0
    payload = json.loads(report.stdout)
    assert payload['ok'] is False
    assert {'kind': 'corrupt_object', 'detail': digest} in payload['issues']

    text = runner.invoke(app, ['doctor', '--report'])
    assert text.exit_code == 0
    assert 'corrupt_object' in text.stdout


def test_report_through_serve_keeps_the_result(tmp_path, monkeypatch):
    from sprout.serve import run_command

    repo, digest = broken_project(tmp_path)
    monkeypatch.chdir(repo.root)
    response = run_command(app, ['doctor', '--report', '--json'])
    assert response['ok'] is True
    assert any(issue['detail'] == digest for issue in response['result']['issues'])


def test_report_on_a_healthy_project(tmp_path, monkeypatch):
    repo = Repository.init(tmp_path / 'project')
    monkeypatch.chdir(repo.root)
    result = CliRunner().invoke(app, ['doctor', '--report', '--json'])
    assert result.exit_code == 0
    assert json.loads(result.stdout)['ok'] is True
