from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone, tzinfo
from pathlib import Path
from typing import Annotated, Any, Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typer
import typer._completion_shared as typer_completion_shared

from . import __version__
from .errors import SproutError
from .repository import (
    CommitAnnotations,
    CommitAttachment,
    CommitGraph,
    FileState,
    GraphCommit,
    Repository,
)

_POWERSHELL_COMPLETION_SCRIPT = """
Import-Module PSReadLine
Set-PSReadLineKeyHandler -Chord Tab -Function MenuComplete
$scriptblock = {
    param($wordToComplete, $commandAst, $cursorPosition)
    $previousComplete = $Env:%(autocomplete_var)s
    $previousArgs = $Env:_TYPER_COMPLETE_ARGS
    $previousWord = $Env:_TYPER_COMPLETE_WORD_TO_COMPLETE
    try {
        $Env:%(autocomplete_var)s = "complete_powershell"
        $Env:_TYPER_COMPLETE_ARGS = $commandAst.ToString()
        $Env:_TYPER_COMPLETE_WORD_TO_COMPLETE = $wordToComplete
        %(prog_name)s | ForEach-Object {
            $commandArray = $_ -Split ":::"
            $command = $commandArray[0]
            $helpString = $commandArray[1]
            [System.Management.Automation.CompletionResult]::new(
                $command, $command, 'ParameterValue', $helpString
            )
        }
    }
    finally {
        if ($null -eq $previousComplete) {
            Remove-Item Env:%(autocomplete_var)s -ErrorAction SilentlyContinue
        }
        else {
            $Env:%(autocomplete_var)s = $previousComplete
        }
        if ($null -eq $previousArgs) {
            Remove-Item Env:_TYPER_COMPLETE_ARGS -ErrorAction SilentlyContinue
        }
        else {
            $Env:_TYPER_COMPLETE_ARGS = $previousArgs
        }
        if ($null -eq $previousWord) {
            Remove-Item Env:_TYPER_COMPLETE_WORD_TO_COMPLETE -ErrorAction SilentlyContinue
        }
        else {
            $Env:_TYPER_COMPLETE_WORD_TO_COMPLETE = $previousWord
        }
    }
}
Register-ArgumentCompleter -Native -CommandName %(prog_name)s -ScriptBlock $scriptblock
"""
_COMPLETION_ENVIRONMENT_VARIABLES = (
    "_SPROUT_COMPLETE",
    "_TYPER_COMPLETE_ARGS",
    "_TYPER_COMPLETE_WORD_TO_COMPLETE",
)


def _install_safe_powershell_completion_template() -> None:
    typer_completion_shared.COMPLETION_SCRIPT_POWER_SHELL = (
        _POWERSHELL_COMPLETION_SCRIPT
    )
    typer_completion_shared._completion_scripts["powershell"] = (
        _POWERSHELL_COMPLETION_SCRIPT
    )
    typer_completion_shared._completion_scripts["pwsh"] = _POWERSHELL_COMPLETION_SCRIPT


_install_safe_powershell_completion_template()

app = typer.Typer(
    add_completion=True,
    no_args_is_help=True,
    help="Offline snapshot version control for local files.",
)
PROGRESS_THRESHOLD = 8 * 1024 * 1024


class _ProgressDisplay:
    def __init__(self) -> None:
        self.enabled = sys.stderr.isatty()
        self._bar: Any = None
        self._label: str | None = None
        self._total = 0
        self._completed = 0

    def __call__(self, label: str, completed: int, total: int) -> None:
        if not self.enabled or total < PROGRESS_THRESHOLD:
            return
        if self._bar is None or label != self._label or total != self._total:
            self.close()
            self._bar = typer.progressbar(
                length=total,
                label=label,
                file=sys.stderr,
                show_pos=True,
            )
            self._bar.__enter__()
            self._label = label
            self._total = total
            self._completed = 0
        self._bar.update(max(0, completed - self._completed))
        self._completed = completed
        if completed >= total:
            self.close()

    def close(self) -> None:
        if self._bar is not None:
            self._bar.__exit__(None, None, None)
        self._bar = None
        self._label = None
        self._total = 0
        self._completed = 0


@contextmanager
def _show_progress(
    repository: Repository, *, enabled: bool = True
) -> Iterator[None]:
    display = _ProgressDisplay()
    previous = repository.progress
    repository.progress = display if enabled and display.enabled else None
    try:
        yield
    finally:
        repository.progress = previous
        display.close()


def _version(value: bool) -> None:
    if value:
        typer.echo(f"sprout {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True)] = False,
) -> None:
    """Manage complete snapshots of project files."""


def repo() -> Repository:
    return Repository.discover()


def _complete_branches() -> list[str]:
    try:
        return [name for name, _commit_id, _comment in repo().branches()]
    except (OSError, SproutError, sqlite3.Error):
        return []


def _complete_references() -> list[str]:
    try:
        repository = repo()
        branches = [name for name, _commit_id, _comment in repository.branches()]
        tags = [name for name, _commit_id, _comment, _created_at in repository.tags()]
        return sorted(branches + tags)
    except (OSError, SproutError, sqlite3.Error):
        return []


def _echo_json(value: Any) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False))


def _echo_json_error(
    code: str, message: str, details: dict[str, Any] | None = None
) -> None:
    typer.echo(
        json.dumps(
            {"code": code, "message": message, "details": details or {}},
            ensure_ascii=False,
        ),
        err=True,
    )


def _json_requested(argv: list[str]) -> bool:
    return "--json" in argv[1:]


def _annotations_json(annotations: CommitAnnotations) -> dict[str, Any]:
    return {
        "note": annotations.note,
        "note_updated_at": annotations.note_updated_at,
        "labels": list(annotations.labels),
    }


def _log_json(
    rows: list[sqlite3.Row], annotations: dict[str, CommitAnnotations]
) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "parent_id": row["parent_id"],
            "created_at": row["created_at"],
            "message": row["message"],
            **_annotations_json(annotations[row["id"]]),
        }
        for row in rows
    ]


def _attachment_json(attachment: CommitAttachment) -> dict[str, Any]:
    return {
        "commit_id": attachment.commit_id,
        "role": attachment.role,
        "original_name": attachment.original_name,
        "media_type": attachment.media_type,
        "object_hash": attachment.object_hash,
        "size": attachment.size,
        "created_at": attachment.created_at,
        "updated_at": attachment.updated_at,
    }


def _show_json(
    row: sqlite3.Row,
    files: list[FileState],
    thumbnail: CommitAttachment | None,
    annotations: CommitAnnotations,
) -> dict[str, Any]:
    return {
        "id": row["id"],
        "parent_id": row["parent_id"],
        "branch_name": row["branch_name"],
        "created_at": row["created_at"],
        "message": row["message"],
        **_annotations_json(annotations),
        "thumbnail": _attachment_json(thumbnail) if thumbnail is not None else None,
        "files": [
            {
                "path": item.path,
                "object_hash": item.object_hash,
                "size": item.size,
                "mtime_ns": item.mtime_ns,
            }
            for item in files
        ],
    }


def _branches_json(repository: Repository) -> list[dict[str, Any]]:
    current = repository.head_branch()
    return [
        {
            "name": name,
            "commit_id": commit_id,
            "comment": comment,
            "current": name == current,
        }
        for name, commit_id, comment in repository.branches()
    ]


def _graph_json(graph: CommitGraph) -> dict[str, Any]:
    return {
        "commits": [
            {
                "id": commit.id,
                "parent_id": commit.parent_id,
                "branch_name": commit.branch_name,
                "created_at": commit.created_at,
                "message": commit.message,
                "attachments": [
                    _attachment_json(attachment)
                    for attachment in commit.attachments
                ],
                "note": commit.note,
                "note_updated_at": commit.note_updated_at,
                "labels": list(commit.labels),
            }
            for commit in graph.commits
        ],
        "branches": [
            {
                "name": branch.name,
                "commit_id": branch.commit_id,
                "comment": branch.comment,
                "current": branch.current,
            }
            for branch in graph.branches
        ],
        "tags": [
            {
                "name": tag.name,
                "commit_id": tag.commit_id,
                "comment": tag.comment,
                "created_at": tag.created_at,
            }
            for tag in graph.tags
        ],
    }


def _tree_text_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def _tree_commit_text(
    commit: GraphCommit,
    branches_by_commit: dict[str, list[str]],
    tags_by_commit: dict[str, list[str]],
) -> str:
    markers = [f"created:{commit.branch_name}"]
    markers.extend(
        f"branch:{branch}" for branch in branches_by_commit.get(commit.id, [])
    )
    markers.extend(f"tag:{tag}" for tag in tags_by_commit.get(commit.id, []))
    for attachment in commit.attachments:
        if attachment.role == "thumbnail":
            markers.append("thumbnail")
        else:
            markers.append(f"attachment:{attachment.role}")
    if commit.note is not None:
        markers.append("note")
    if commit.labels:
        markers.append(
            f"labels:{','.join(_tree_text_value(label) for label in commit.labels)}"
        )
    suffix = " ".join(f"[{marker}]" for marker in markers)
    return f"{commit.id[:12]} {_tree_text_value(commit.message)} {suffix}"


def _tree_lines(graph: CommitGraph) -> list[str]:
    if not graph.commits:
        return []
    branches_by_commit: dict[str, list[str]] = {}
    for branch in graph.branches:
        if branch.commit_id is not None:
            marker = f"{'*' if branch.current else ''}{branch.name}"
            branches_by_commit.setdefault(branch.commit_id, []).append(marker)
    tags_by_commit: dict[str, list[str]] = {}
    for tag in graph.tags:
        tags_by_commit.setdefault(tag.commit_id, []).append(tag.name)
    children: dict[str | None, list[GraphCommit]] = {}
    commit_ids = {commit.id for commit in graph.commits}
    for commit in graph.commits:
        parent = commit.parent_id if commit.parent_id in commit_ids else None
        children.setdefault(parent, []).append(commit)
    for items in children.values():
        items.sort(key=lambda item: (item.created_at, item.id))

    lines: list[str] = []
    for root in children.get(None, []):
        lines.append(
            f"* {_tree_commit_text(root, branches_by_commit, tags_by_commit)}"
        )
        root_children = children.get(root.id, [])
        stack: list[tuple[GraphCommit, str, bool]] = [
            (child, "", index == len(root_children) - 1)
            for index, child in reversed(list(enumerate(root_children)))
        ]
        while stack:
            commit, prefix, is_last = stack.pop()
            connector = "`- " if is_last else "|- "
            text = _tree_commit_text(commit, branches_by_commit, tags_by_commit)
            lines.append(f"{prefix}{connector}* {text}")
            child_prefix = prefix + ("   " if is_last else "|  ")
            nested = children.get(commit.id, [])
            for index, child in reversed(list(enumerate(nested))):
                stack.append((child, child_prefix, index == len(nested) - 1))
    return lines


def _display_timezone(name: str) -> tzinfo | None:
    if name.lower() == "local":
        return None
    if name.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise SproutError(f"unknown timezone: {name}") from exc


def _format_datetime(value: datetime, display_timezone: tzinfo | None) -> str:
    converted = value.astimezone() if display_timezone is None else value.astimezone(display_timezone)
    zone_name = converted.tzname() or converted.strftime("%z")
    return f"{converted:%Y-%m-%d %H:%M:%S} {zone_name}"


@app.command()
def init(
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Initialize a Sprout project."""
    created = Repository.init(path)
    if json_output:
        _echo_json({"root": str(created.root)})
        return
    typer.echo(f"Initialized Sprout project in {created.root}")


@app.command()
def track(
    paths: Annotated[list[Path], typer.Argument(help="Files or directories to track")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Register files for future commits."""
    added = repo().track(paths)
    if json_output:
        _echo_json({"paths": added})
        return
    if not added:
        typer.echo("Warning: no files were tracked", err=True)
        return
    for path in added:
        typer.echo(f"track  {path}")


@app.command()
def untrack(
    paths: Annotated[list[Path], typer.Argument(help="Files or directories to stop tracking")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Stop tracking paths without deleting working files."""
    removed = repo().untrack(paths)
    if json_output:
        _echo_json({"paths": removed})
        return
    if not removed:
        typer.echo("Warning: no matching tracked paths", err=True)
        return
    for path in removed:
        typer.echo(f"untrack  {path}")


@app.command()
def move(
    source: Annotated[Path, typer.Argument(help="Tracked file to move")],
    destination: Annotated[Path, typer.Argument(help="New path for the tracked file")],
) -> None:
    """Move a tracked file and update its tracked path."""
    old, new = repo().move(source, destination)
    typer.echo(f"move  {old} -> {new}")


@app.command()
def status(
    paths: Annotated[list[Path] | None, typer.Argument(help="Paths whose tracking state should be checked")] = None,
    tracked: Annotated[bool, typer.Option("--tracked", help="List every tracked file")] = False,
    untracked: Annotated[bool, typer.Option("--untracked", help="List every untracked file")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """Show changes or whether specific paths are tracked."""
    repository = repo()
    branch_name = repository.head_branch()
    if paths:
        if tracked or untracked:
            raise SproutError("path status cannot be combined with --tracked or --untracked")
        path_entries = repository.tracking_status(paths)
        if json_output:
            _echo_json(
                {
                    "branch": branch_name,
                    "paths": [
                        {"path": path, "tracked": is_tracked}
                        for path, is_tracked in path_entries
                    ],
                }
            )
            return
        typer.echo(f"On branch {branch_name}")
        for path, is_tracked in path_entries:
            typer.echo(f"{'tracked' if is_tracked else 'untracked':<9} {path}")
        return
    with _show_progress(repository, enabled=not json_output):
        entries = repository.status()
    if json_output:
        payload: dict[str, Any] = {
            "branch": branch_name,
            "changes": [{"state": entry.state, "path": entry.path} for entry in entries],
        }
        if tracked:
            payload["tracked"] = sorted(repository.tracked())
        if untracked:
            payload["untracked"] = repository.untracked_files()
        _echo_json(payload)
        return
    typer.echo(f"On branch {branch_name}")
    if not entries:
        typer.echo("Working tree clean")
    for entry in entries:
        typer.echo(f"{entry.state:<8} {entry.path}")
    if tracked:
        typer.echo("\nTracked files:")
        tracked_paths = sorted(repository.tracked())
        if not tracked_paths:
            typer.echo("  (none)")
        for path in tracked_paths:
            typer.echo(f"  {path}")
    if untracked:
        typer.echo("\nUntracked files:")
        untracked_paths = repository.untracked_files()
        if not untracked_paths:
            typer.echo("  (none)")
        for path in untracked_paths:
            typer.echo(f"  {path}")


@app.command(name="commit")
def commit_command(
    message: Annotated[str, typer.Option("--message", "-m")],
    thumbnail: Annotated[
        Path | None,
        typer.Option("--thumbnail", help="PNG, JPEG, or WebP thumbnail image"),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Save a snapshot of all tracked files."""
    repository = repo()
    with _show_progress(repository, enabled=not json_output):
        result = repository.commit(message, thumbnail=thumbnail)
    if json_output:
        _echo_json(
            {
                "id": result.commit_id,
                "branch": repository.head_branch(),
                "message": message.strip(),
                "removed_paths": list(result.removed_paths),
            }
        )
        return
    for path in result.removed_paths:
        typer.echo(f"deleted  {path}")
    typer.echo(f"[{repository.head_branch()} {result.commit_id[:12]}] {message.strip()}")


@app.command(name="log")
def log_command(
    path: Annotated[
        Path | None,
        typer.Argument(help="Show only commits that changed this path"),
    ] = None,
    max_count: Annotated[
        int | None,
        typer.Option(
            "--max-count",
            "-n",
            min=1,
            help="Limit the number of displayed commits",
        ),
    ] = None,
    oneline: Annotated[
        bool,
        typer.Option("--oneline", help="Show each commit as a one-line summary"),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
    label: Annotated[
        str | None,
        typer.Option("--label", help="Show commits with this exact label"),
    ] = None,
) -> None:
    """Show history of the current branch."""
    if json_output and oneline:
        raise SproutError("--json and --oneline cannot be used together")
    repository = repo()
    rows = repository.log(path, limit=max_count, label=label)
    annotations = repository.annotations_many([row["id"] for row in rows])
    if json_output:
        _echo_json(_log_json(rows, annotations))
        return
    if not rows:
        if path is not None:
            typer.echo(f"No history for path: {path.as_posix()}")
        else:
            typer.echo("No commits yet")
        return
    for row in rows:
        if oneline:
            typer.echo(f"{row['id'][:12]} {row['message']}")
            continue
        typer.echo(f"commit {row['id']}")
        typer.echo(f"Date:   {row['created_at']}")
        annotation = annotations[row["id"]]
        if annotation.labels:
            typer.echo(f"Labels: {', '.join(annotation.labels)}")
        if annotation.note is not None:
            typer.echo(f"Note:   {annotation.note.replace(chr(10), chr(10) + '        ')}")
            typer.echo(f"Note updated: {annotation.note_updated_at}")
        typer.echo(f"\n    {row['message']}\n")


@app.command()
def tree(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output the complete commit graph as JSON"),
    ] = False,
) -> None:
    """Show every commit and current reference in the repository."""
    graph = repo().commit_graph()
    if json_output:
        _echo_json(_graph_json(graph))
        return
    lines = _tree_lines(graph)
    if not lines:
        typer.echo("No commits yet")
        return
    for line in lines:
        typer.echo(line)


@app.command()
def diff(
    commit_a: Annotated[
        str | None,
        typer.Argument(help="First commit, or the commit to compare against the working tree"),
    ] = None,
    commit_b: Annotated[
        str | None,
        typer.Argument(help="Second commit; omit to compare against the working tree"),
    ] = None,
) -> None:
    """Show file-level differences between commits or the working tree."""
    repository = repo()
    with _show_progress(repository):
        entries = repository.diff(commit_a, commit_b)
    if not entries:
        typer.echo("No differences")
        return
    for entry in entries:
        if entry.state == "modified" and entry.old_size is not None and entry.new_size is not None:
            typer.echo(
                f"{entry.state:<8} {entry.path}  ({entry.old_size} bytes -> {entry.new_size} bytes)"
            )
        elif entry.state == "added" and entry.new_size is not None:
            typer.echo(f"{entry.state:<8} {entry.path}  ({entry.new_size} bytes)")
        elif entry.state == "deleted" and entry.old_size is not None:
            typer.echo(f"{entry.state:<8} {entry.path}  ({entry.old_size} bytes)")
        else:
            typer.echo(f"{entry.state:<8} {entry.path}")


@app.command()
def show(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    timezone_name: Annotated[
        str,
        typer.Option(
            "--timezone",
            help="Display timezone: UTC, local, or an IANA name such as Asia/Tokyo",
        ),
    ] = "UTC",
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """Show a commit and its files."""
    repository = repo()
    row, files = repository.commit_info(commit)
    thumbnail = repository.thumbnail(row["id"])
    annotations = repository.annotations(row["id"])
    if json_output:
        if timezone_name.upper() != "UTC":
            raise SproutError("--timezone cannot be used with --json")
        _echo_json(_show_json(row, files, thumbnail, annotations))
        return
    display_timezone = _display_timezone(timezone_name)
    created_at = datetime.fromisoformat(row["created_at"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    typer.echo(f"commit {row['id']}")
    typer.echo(f"Parent: {row['parent_id'] or '-'}")
    typer.echo(f"Branch: {row['branch_name']}")
    typer.echo(f"Date:   {_format_datetime(created_at, display_timezone)}")
    if annotations.labels:
        typer.echo(f"Labels: {', '.join(annotations.labels)}")
    if annotations.note is not None:
        typer.echo(
            f"Note:   {annotations.note.replace(chr(10), chr(10) + '        ')}"
        )
        typer.echo(f"Note updated: {annotations.note_updated_at}")
    typer.echo(f"\n    {row['message']}\n")
    if thumbnail is not None:
        typer.echo(
            f"Thumbnail: {thumbnail.original_name} "
            f"({thumbnail.media_type}, {thumbnail.size} bytes)"
        )
    for item in files:
        modified_at = datetime.fromtimestamp(item.mtime_ns // 1_000_000_000, tz=timezone.utc)
        typer.echo(
            f"{item.object_hash[:12]}  {item.size:>10}  "
            f"{_format_datetime(modified_at, display_timezone)}  {item.path}"
        )


@app.command()
def thumbnail(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    image: Annotated[
        Path | None,
        typer.Argument(help="PNG, JPEG, or WebP image to register"),
    ] = None,
    delete: Annotated[
        bool,
        typer.Option("--delete", help="Delete the registered thumbnail"),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write the thumbnail to this file"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing output file"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output structured thumbnail metadata"),
    ] = False,
) -> None:
    """Inspect, register, delete, or export a commit thumbnail."""
    operations = sum((image is not None, delete, output is not None))
    if operations > 1:
        raise SproutError("image, --delete, and --output cannot be combined")
    if force and output is None:
        raise SproutError("--force requires --output")
    repository = repo()
    if image is not None:
        with _show_progress(repository, enabled=not json_output):
            attachment = repository.set_thumbnail(commit, image)
        if json_output:
            _echo_json(_attachment_json(attachment))
            return
        typer.echo(
            f"Set thumbnail for {attachment.commit_id[:12]}: "
            f"{attachment.original_name}"
        )
        return
    if delete:
        attachment = repository.delete_thumbnail(commit)
        if json_output:
            _echo_json({**_attachment_json(attachment), "deleted": True})
            return
        typer.echo(f"Deleted thumbnail from {attachment.commit_id[:12]}")
        return
    if output is not None:
        with _show_progress(repository, enabled=not json_output):
            destination = repository.export_thumbnail(commit, output, force=force)
        if json_output:
            _echo_json({"output": str(destination)})
            return
        typer.echo(f"Exported thumbnail to {destination}")
        return

    attachment = repository.thumbnail(commit)
    if json_output:
        _echo_json(_attachment_json(attachment) if attachment is not None else None)
        return
    if attachment is None:
        typer.echo("No thumbnail")
        return
    typer.echo(f"Thumbnail for {attachment.commit_id}")
    typer.echo(f"File:    {attachment.original_name}")
    typer.echo(f"Type:    {attachment.media_type}")
    typer.echo(f"Size:    {attachment.size}")
    typer.echo(f"Created: {attachment.created_at}")
    typer.echo(f"Updated: {attachment.updated_at}")


@app.command()
def note(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    text: Annotated[
        str | None,
        typer.Argument(help="Note text to set; omit to inspect"),
    ] = None,
    delete: Annotated[
        bool,
        typer.Option("--delete", help="Delete the commit note"),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Inspect, set, or delete an editable commit note."""
    if text is not None and delete:
        raise SproutError("note text and --delete cannot be combined")
    repository = repo()
    if text is not None or delete:
        annotations = repository.set_note(commit, "" if delete else text or "")
        if json_output:
            _echo_json(
                {"commit_id": annotations.commit_id, **_annotations_json(annotations)}
            )
            return
        if annotations.note is None:
            typer.echo(f"Deleted note from {annotations.commit_id[:12]}")
        else:
            typer.echo(f"Set note for {annotations.commit_id[:12]}")
        return
    annotations = repository.annotations(commit)
    if json_output:
        _echo_json(
            {"commit_id": annotations.commit_id, **_annotations_json(annotations)}
        )
        return
    if annotations.note is None:
        typer.echo("No note")
        return
    typer.echo(f"Note for {annotations.commit_id}")
    typer.echo(f"Updated: {annotations.note_updated_at}")
    typer.echo(annotations.note)


@app.command()
def label(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    value: Annotated[
        str | None,
        typer.Argument(help="Label to add; omit to inspect"),
    ] = None,
    delete: Annotated[
        str | None,
        typer.Option("--delete", help="Label to remove"),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Inspect, add, or remove editable commit labels."""
    if value is not None and delete is not None:
        raise SproutError("label value and --delete cannot be combined")
    repository = repo()
    if value is not None:
        annotations = repository.add_label(commit, value)
        if json_output:
            _echo_json(
                {"commit_id": annotations.commit_id, **_annotations_json(annotations)}
            )
            return
        typer.echo(f"Added label to {annotations.commit_id[:12]}: {value.strip()}")
        return
    if delete is not None:
        annotations = repository.remove_label(commit, delete)
        if json_output:
            _echo_json(
                {"commit_id": annotations.commit_id, **_annotations_json(annotations)}
            )
            return
        typer.echo(f"Removed label from {annotations.commit_id[:12]}: {delete.strip()}")
        return
    annotations = repository.annotations(commit)
    if json_output:
        _echo_json(
            {"commit_id": annotations.commit_id, **_annotations_json(annotations)}
        )
        return
    if not annotations.labels:
        typer.echo("No labels")
        return
    for item in annotations.labels:
        typer.echo(item)


@app.command()
def branch(
    name: Annotated[str | None, typer.Argument()] = None,
    start_point: Annotated[
        str | None,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag; defaults to current branch tip",
            autocompletion=_complete_references,
        ),
    ] = None,
    comment: Annotated[str, typer.Option("--comment", "-m", help="Comment for a new branch")] = "",
    set_comment: Annotated[
        str | None, typer.Option("--set-comment", help="Replace an existing branch comment")
    ] = None,
    delete: Annotated[
        str | None, typer.Option("--delete", help="Delete a branch")
    ] = None,
    rename: Annotated[
        str | None,
        typer.Option("--rename", help="Rename the branch given by NAME"),
    ] = None,
    switch: Annotated[
        bool,
        typer.Option(
            "--switch",
            help="Create the branch and switch to it, restoring the start point",
        ),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """List, create, delete, rename, or edit a branch."""
    repository = repo()
    if delete is not None:
        if (
            name is not None
            or start_point is not None
            or comment
            or set_comment is not None
            or rename is not None
            or switch
        ):
            raise SproutError("--delete cannot be combined with other branch operations")
        repository.delete_branch(delete)
        if json_output:
            _echo_json({"name": delete, "deleted": True})
            return
        typer.echo(f"Deleted branch {delete}")
        return
    if rename is not None:
        if name is None:
            raise SproutError("a branch name is required with --rename")
        if start_point is not None or comment or set_comment is not None or switch:
            raise SproutError("--rename cannot be combined with comment options")
        repository.rename_branch(name, rename)
        if json_output:
            _echo_json({"name": rename, "previous_name": name})
            return
        typer.echo(f"Renamed branch {name} to {rename}")
        return
    if set_comment is not None:
        if name is None:
            raise SproutError("a branch name is required with --set-comment")
        if start_point is not None or comment or switch:
            raise SproutError("--comment and --set-comment cannot be used together")
        repository.set_branch_comment(name, set_comment)
        if json_output:
            _echo_json({"name": name, "comment": set_comment.strip()})
            return
        typer.echo(f"Updated comment for branch {name}")
        return
    if name is not None:
        with _show_progress(repository, enabled=not json_output):
            commit_id = repository.create_branch(
                name, comment, start_point=start_point, switch=switch
            )
        if json_output:
            _echo_json(
                {
                    "name": name,
                    "commit_id": commit_id,
                    "comment": comment.strip(),
                    "current": switch,
                }
            )
            return
        if switch:
            typer.echo(f"Created and switched to branch {name}")
        else:
            typer.echo(f"Created branch {name}")
        return
    if start_point is not None or switch:
        raise SproutError("a branch name is required")
    if comment:
        raise SproutError("a branch name is required with --comment")
    if json_output:
        _echo_json(_branches_json(repository))
        return
    current = repository.head_branch()
    for branch_name, commit_id, branch_comment in repository.branches():
        marker = "*" if branch_name == current else " "
        suffix = f"  # {branch_comment}" if branch_comment else ""
        typer.echo(f"{marker} {branch_name:<20} {(commit_id or '-')[:12]}{suffix}")


@app.command()
def tag(
    name: Annotated[str | None, typer.Argument(help="Tag name")] = None,
    commit: Annotated[
        str | None,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag; defaults to HEAD",
            autocompletion=_complete_references,
        ),
    ] = None,
    comment: Annotated[
        str, typer.Option("--comment", "-m", help="Comment for a new tag")
    ] = "",
    delete: Annotated[
        str | None, typer.Option("--delete", help="Delete a tag")
    ] = None,
) -> None:
    """List, create, or delete tags."""
    repository = repo()
    if delete is not None:
        if name is not None or commit is not None or comment:
            raise SproutError("--delete cannot be combined with tag creation arguments")
        repository.delete_tag(delete)
        typer.echo(f"Deleted tag {delete}")
        return
    if name is not None:
        commit_id = repository.create_tag(name, commit, comment)
        typer.echo(f"Created tag {name} at {commit_id[:12]}")
        return
    if commit is not None or comment:
        raise SproutError("a tag name is required")
    tags = repository.tags()
    if not tags:
        typer.echo("No tags")
        return
    for tag_name, commit_id, tag_comment, _created_at in tags:
        suffix = f"  # {tag_comment}" if tag_comment else ""
        typer.echo(f"{tag_name:<20} {commit_id[:12]}{suffix}")


@app.command(name="switch")
def switch_command(
    branch_name: Annotated[
        str, typer.Argument(autocompletion=_complete_branches)
    ],
    discard: Annotated[
        bool,
        typer.Option(
            "--discard",
            help="Discard all tracked changes; leave untracked files untouched",
        ),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Switch to a branch and restore its tip."""
    repository = repo()
    with _show_progress(repository, enabled=not json_output):
        commit_id = repository.switch(branch_name, discard=discard)
    if json_output:
        _echo_json({"branch": branch_name, "commit_id": commit_id})
        return
    typer.echo(f"Switched to branch {branch_name}")


@app.command()
def restore(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Optional files or directories to restore from the commit"),
    ] = None,
    discard: Annotated[
        bool,
        typer.Option(
            "--discard",
            help="Discard tracked changes on restored paths; leave other files untouched",
        ),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Restore a snapshot, or only selected paths, without moving the branch tip."""
    repository = repo()
    with _show_progress(repository, enabled=not json_output):
        commit_id = repository.restore(commit, paths, discard=discard)
    if json_output:
        _echo_json(
            {
                "commit_id": commit_id,
                "paths": [path.as_posix() for path in paths] if paths else None,
            }
        )
        return
    if paths:
        typer.echo(f"Restored paths from {commit_id[:12]} (branch tip unchanged)")
    else:
        typer.echo(f"Restored {commit_id[:12]} (branch tip unchanged)")


@app.command(name="export")
def export_command(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory to write exported files"),
    ],
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Optional files or directories to export"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing output files"),
    ] = False,
) -> None:
    """Write files from a commit without changing the working tree."""
    repository = repo()
    with _show_progress(repository):
        result = repository.export(commit, output, paths, force=force)
    for path in result.paths:
        typer.echo(f"export  {path}")
    typer.echo(
        f"Exported {len(result.paths)} file(s) from {result.commit_id[:12]} "
        f"to {output.resolve()}"
    )


@app.command(name="cat")
def cat_command(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    path: Annotated[Path, typer.Argument(help="File to write to standard output")],
) -> None:
    """Write one file from a commit to standard output."""
    repository = repo()
    with _show_progress(repository):
        repository.cat(commit, path, sys.stdout.buffer)


@app.command()
def gc(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List reclaimable objects without deleting them"),
    ] = False,
) -> None:
    """Delete unreferenced objects and leftover temporary object files."""
    result = repo().gc(dry_run=dry_run)
    if dry_run:
        for object_hash in result.objects:
            typer.echo(f"object  {object_hash}")
        for name in result.temps:
            typer.echo(f"temp    {name}")
    action = "Would remove" if dry_run else "Removed"
    typer.echo(
        f"{action} {result.removed_objects} objects, "
        f"{result.removed_temps} temp files ({result.freed_bytes} bytes)"
    )


@app.command()
def doctor() -> None:
    """Inspect repository integrity without changing files."""
    result = repo().doctor()
    for issue in result.issues:
        typer.echo(f"{issue.kind:<18} {issue.detail}")
    if result.ok:
        typer.echo(f"OK ({result.checked_objects} objects checked)")
        return
    typer.echo(
        f"Found {len(result.issues)} issue(s) ({result.checked_objects} objects checked)"
    )
    raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Show repository size and basic counts."""
    result = repo().stats()
    typer.echo(f"Commits:       {result.commits}")
    typer.echo(f"Branches:      {result.branches}")
    typer.echo(f"Tracked paths: {result.tracked_paths}")
    typer.echo(f"Objects:       {result.objects} ({result.objects_bytes} bytes)")
    typer.echo(f"Logical size:  {result.logical_bytes} bytes")
    typer.echo(f"Unique size:   {result.unique_bytes} bytes")
    typer.echo(f"Dedup saved:   {result.dedup_saved_bytes} bytes")


def _system_exit_code(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return 1


def _handle_cli_exception(
    exc: BaseException, *, json_output: bool = False
) -> int | None:
    show = getattr(exc, "show", None)
    exit_code = getattr(exc, "exit_code", None)
    if callable(show) and isinstance(exit_code, int):
        if json_output:
            format_message = getattr(exc, "format_message", None)
            message = format_message() if callable(format_message) else str(exc)
            _echo_json_error(
                "usage_error", message, {"exit_code": exit_code}
            )
            return exit_code
        show()
        return exit_code
    return None


def _clear_stale_completion_environment(argv: list[str]) -> None:
    if len(argv) <= 1:
        return
    instruction = os.environ.get("_SPROUT_COMPLETE", "")
    if not instruction.startswith("complete_"):
        return
    for name in _COMPLETION_ENVIRONMENT_VARIABLES:
        os.environ.pop(name, None)


def main() -> int:
    _clear_stale_completion_environment(sys.argv)
    json_output = _json_requested(sys.argv)
    try:
        app(standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except SystemExit as exc:
        return _system_exit_code(exc.code)
    except SproutError as exc:
        if json_output:
            _echo_json_error(exc.code, str(exc), exc.details)
        else:
            typer.echo(f"Error: {exc}", err=True)
        return 1
    except (OSError, sqlite3.Error) as exc:
        message = f"repository operation failed: {exc}"
        if json_output:
            _echo_json_error(
                "repository_error", message, {"type": type(exc).__name__}
            )
        else:
            typer.echo(f"Error: {message}", err=True)
        return 1
    except BaseException as exc:
        exit_code = _handle_cli_exception(exc, json_output=json_output)
        if exit_code is None:
            raise
        return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
