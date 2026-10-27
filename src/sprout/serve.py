"""JSON Lines request loop that runs CLI commands without restarting Python."""
from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, TextIO

import typer

from .errors import SproutError

PROTOCOL_VERSION = 1


def _error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details or {}}


def _parse_output(text: str) -> Any:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def _structured_stderr(text: str) -> dict[str, Any] | None:
    for line in reversed(text.strip().splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and {"code", "message"} <= value.keys():
            return {
                "code": value["code"],
                "message": value["message"],
                "details": value.get("details") or {},
            }
    return None


def run_command(app: typer.Typer, args: list[str]) -> dict[str, Any]:
    """Run one CLI invocation in-process and describe the result."""
    stdout, stderr = io.StringIO(), io.StringIO()
    exit_code = 0
    error: dict[str, Any] | None = None
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            result = app(args=args, prog_name="sprout", standalone_mode=False)
            if isinstance(result, int):
                exit_code = result
        except typer.Exit as exc:
            exit_code = exc.exit_code
        except typer.Abort:
            exit_code = 1
            error = _error("aborted", "command was aborted")
        except SproutError as exc:
            exit_code = 1
            error = _error(exc.code, str(exc), exc.details)
        except (OSError, sqlite3.Error) as exc:
            exit_code = 1
            error = _error(
                "repository_error",
                f"repository operation failed: {exc}",
                {"type": type(exc).__name__},
            )
        except Exception as exc:
            # Usage errors from the bundled click carry an exit code and a message.
            format_message = getattr(exc, "format_message", None)
            code = getattr(exc, "exit_code", None)
            if not callable(format_message) or not isinstance(code, int):
                raise
            exit_code = code
            error = _error("usage_error", format_message(), {"exit_code": code})
    response: dict[str, Any] = {"ok": exit_code == 0 and error is None, "exit_code": exit_code}
    output = _parse_output(stdout.getvalue())
    if response["ok"]:
        response["result"] = output
        return response
    if error is None:
        error = _structured_stderr(stderr.getvalue()) or _error(
            "command_failed",
            stderr.getvalue().strip() or f"command exited with {exit_code}",
            {"exit_code": exit_code},
        )
    if output is not None:
        response["result"] = output
    response["error"] = error
    return response


def _handle(app: typer.Typer, request: Any) -> tuple[dict[str, Any], bool]:
    if not isinstance(request, dict):
        return {"id": None, "ok": False, "error": _error("invalid_request", "request must be an object")}, False
    request_id = request.get("id")
    if request.get("command") == "quit":
        return {"id": request_id, "ok": True, "result": None}, True
    args = request.get("args")
    if not isinstance(args, list) or not args or not all(isinstance(item, str) for item in args):
        return {
            "id": request_id,
            "ok": False,
            "error": _error("invalid_request", "args must be a non-empty list of strings"),
        }, False
    if args[0] == "serve":
        return {
            "id": request_id,
            "ok": False,
            "error": _error("invalid_request", "serve cannot be nested"),
        }, False
    cwd = request.get("cwd")
    if cwd is not None and not isinstance(cwd, str):
        return {"id": request_id, "ok": False, "error": _error("invalid_request", "cwd must be a string")}, False
    previous = os.getcwd()
    try:
        if cwd is not None:
            try:
                os.chdir(Path(cwd))
            except OSError as exc:
                return {
                    "id": request_id,
                    "ok": False,
                    "error": _error("invalid_cwd", f"cannot use directory: {cwd}", {"reason": str(exc)}),
                }, False
        return {"id": request_id, **run_command(app, list(args))}, False
    finally:
        os.chdir(previous)


def serve(
    app: typer.Typer,
    version: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Answer one JSON request per input line until EOF or a quit request."""
    source = stdin if stdin is not None else sys.stdin
    sink = stdout if stdout is not None else sys.stdout
    def write(value: dict[str, Any]) -> None:
        sink.write(json.dumps(value, ensure_ascii=False) + "\n")
        sink.flush()

    write({"ready": True, "version": version, "protocol": PROTOCOL_VERSION})
    for line in source:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            write({"id": None, "ok": False, "error": _error("invalid_json", str(exc))})
            continue
        response, stop = _handle(app, request)
        write(response)
        if stop:
            return
