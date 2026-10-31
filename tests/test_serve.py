"""Round trips through the JSON Lines serve mode."""
import io
import json
import subprocess
import sys
from pathlib import Path

from sprout import __version__
from sprout.cli import app
from sprout.repository import Repository
from sprout.serve import serve


def exchange(requests: list[object], cwd: Path, monkeypatch) -> list[dict]:
    monkeypatch.chdir(cwd)
    source = io.StringIO(
        "".join(
            (item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)) + "\n"
            for item in requests
        )
    )
    sink = io.StringIO()
    serve(app, __version__, source, sink)
    return [json.loads(line) for line in sink.getvalue().splitlines()]


def test_serve_answers_reads_and_writes_like_the_cli(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "絵.psd").write_bytes(b"v1")

    responses = exchange(
        [
            {"id": 1, "args": ["init", ".", "--json"]},
            {"id": 2, "args": ["file", "track", "絵.psd", "--json"]},
            {"id": 3, "args": ["leaf", "create", "-m", "最初", "--json"]},
            {"id": "s", "args": ["status", "--json"]},
            {"id": 5, "args": ["leaf", "tree", "--json"]},
        ],
        project,
        monkeypatch,
    )

    assert responses[0] == {"ready": True, "version": __version__, "protocol": 1}
    assert [item["id"] for item in responses[1:]] == [1, 2, 3, "s", 5]
    assert all(item["ok"] and item["exit_code"] == 0 for item in responses[1:])
    commit = responses[3]["result"]
    assert (commit["branch"], commit["message"], commit["created_branch"]) == ("main", "最初", False)
    assert responses[4]["result"] == {
        "branch": "main",
        "branch_id": commit["branch_id"],
        "current_commit": commit["id"],
        "at_branch_tip": True,
        "changes": [],
    }
    assert [item["id"] for item in responses[5]["result"]["commits"]] == [commit["id"]]


def test_serve_runs_position_bud_go_and_auto_branch_commands(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    repo = Repository.init(project)
    monkeypatch.chdir(project)
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    repo.track([asset])
    first = repo.commit("first").commit_id
    asset.write_bytes(b"v2")
    second = repo.commit("second").commit_id
    asset.write_bytes(b"draft")

    responses = exchange(
        [
            {"id": 1, "args": ["go", first, "--json"]},
            {"id": 2, "args": ["bud", "list", "--json"]},
            {"id": 3, "args": ["status", "--json"]},
        ],
        project,
        monkeypatch,
    )
    moved, buds, status = responses[1:]
    assert moved["result"]["current_commit"] == first
    assert moved["result"]["bud"]["base_commit_id"] == second
    assert [item["id"] for item in buds["result"]] == [moved["result"]["bud"]["id"]]
    assert (status["result"]["current_commit"], status["result"]["at_branch_tip"]) == (first, False)

    asset.write_bytes(b"alternative")
    committed = exchange(
        [{"id": 4, "args": ["leaf", "create", "-m", "alt", "--json"]}], project, monkeypatch
    )[1]
    assert committed["ok"]
    assert committed["result"]["created_branch"] is True


def test_serve_reports_errors_and_keeps_running(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    Repository.init(project)

    responses = exchange(
        [
            "not json",
            [1, 2],
            {"id": 1, "args": []},
            {"id": 2, "args": ["serve"]},
            {"id": 3, "args": ["go", "missing", "--keep-branch", "--reject-changes", "--json"]},
            {"id": 4, "args": ["--no-such-option"]},
            {"id": 5, "args": ["status", "--json"], "cwd": str(tmp_path / "missing")},
            {"id": 6, "args": ["maintenance", "doctor"]},
            {"id": 7, "command": "quit"},
            {"id": 8, "args": ["status", "--json"]},
        ],
        project,
        monkeypatch,
    )

    codes = [item.get("error", {}).get("code") for item in responses[1:]]
    assert codes == [
        "invalid_json",
        "invalid_request",
        "invalid_request",
        "invalid_request",
        "unknown_commit",
        "usage_error",
        "invalid_cwd",
        None,
        None,
    ]
    assert responses[8]["result"] == {"text": "OK (0 objects checked)\n"}
    assert responses[-1] == {"id": 7, "ok": True, "result": None}


def test_serve_uses_request_cwd_and_restores_it(tmp_path: Path, monkeypatch) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    Repository.init(first)
    Repository.init(second)
    (second / "only.bin").write_bytes(b"x")

    responses = exchange(
        [
            {"id": 1, "args": ["file", "track", "only.bin", "--json"], "cwd": str(second)},
            {"id": 2, "args": ["status", "--json", "--tracked"]},
        ],
        first,
        monkeypatch,
    )

    assert responses[1]["result"] == {"paths": ["only.bin"]}
    assert responses[2]["result"]["tracked"] == []
    assert Path.cwd() == first


def test_serve_process_coexists_with_other_cli_processes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    repo = Repository.init(project)
    asset = project / "asset.bin"
    asset.write_bytes(b"v1")
    repo.track([asset])
    process = subprocess.Popen(
        [sys.executable, "-m", "sprout", "serve"],
        cwd=project,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    def ask(request: dict) -> dict:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        return json.loads(process.stdout.readline())

    try:
        assert json.loads(process.stdout.readline())["ready"] is True
        external = subprocess.run(
            [sys.executable, "-m", "sprout", "commit", "-m", "outside", "--json"],
            cwd=project,
            capture_output=True,
            encoding="utf-8",
            check=True,
        )
        outside = json.loads(external.stdout)["id"]
        assert ask({"id": 1, "args": ["status", "--json"]})["result"]["current_commit"] == outside

        asset.write_bytes(b"v2")
        with repo.lock():
            locked = ask({"id": 2, "args": ["leaf", "create", "-m", "blocked", "--json"]})
        assert locked["ok"] is False
        assert locked["error"]["code"] == "repository_locked"
        retried = ask({"id": 3, "args": ["leaf", "create", "-m", "after", "--json"]})
        assert retried["ok"] is True
        assert ask({"id": 4, "command": "quit"}) == {"id": 4, "ok": True, "result": None}
        assert process.wait(timeout=30) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
