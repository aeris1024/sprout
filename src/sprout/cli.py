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
    ArchivePlan,
    Bud,
    CommitAnnotations,
    CommitAttachment,
    CommitDeletion,
    CommitGraph,
    DeletedBranch,
    FileState,
    GraphCommit,
    PreviewPlan,
    PruneResult,
    Repository,
    StatusEntry,
    UNCHANGED,
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
leaf_app = typer.Typer(no_args_is_help=True, help="Create and manage saved leaves.")
file_app = typer.Typer(no_args_is_help=True, help="Manage tracked files and their contents.")
maintenance_app = typer.Typer(no_args_is_help=True, help="Inspect and maintain project storage.")
app.add_typer(leaf_app, name="leaf")
app.add_typer(file_app, name="file")
app.add_typer(maintenance_app, name="maintenance")


@file_app.callback()
def file_group() -> None:
    """Manage tracked files and their contents."""


@maintenance_app.callback()
def maintenance_group() -> None:
    """Inspect and maintain project storage."""


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
        "id": attachment.id,
        "position": attachment.position,
        "commit_id": attachment.commit_id,
        "role": attachment.role,
        "original_name": attachment.original_name,
        "display_name": attachment.display_name, "description": attachment.description,
        "file_ids": list(attachment.file_ids),
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
    attachments: tuple[CommitAttachment, ...],
) -> dict[str, Any]:
    return {
        "id": row["id"],
        "parent_id": row["parent_id"],
        "branch_name": row["branch_name"],
        "branch_id": row["branch_id"],
        "created_at": row["created_at"],
        "message": row["message"],
        **_annotations_json(annotations),
        "thumbnail": _attachment_json(thumbnail) if thumbnail is not None else None,
        "attachments": [_attachment_json(item) for item in attachments],
        "files": [
            {
                "path": item.path,
                "object_hash": item.object_hash,
                "size": item.size,
                "mtime_ns": item.mtime_ns,
                "file_id": item.file_id,
            }
            for item in files
        ],
    }


def _branches_json(repository: Repository) -> list[dict[str, Any]]:
    return [
        {
            "id": branch.id,
            "name": branch.name,
            "commit_id": branch.commit_id,
            "comment": branch.comment,
            "current": branch.current,
            "created_at": branch.created_at,
        }
        for branch in repository.branch_references()
    ]


def _tag_json(repository: Repository, name: str) -> dict[str, Any]:
    for tag_name, commit_id, comment, created_at in repository.tags():
        if tag_name == name:
            return {"name": tag_name, "commit_id": commit_id, "comment": comment, "created_at": created_at}
    raise SproutError(f"unknown tag: {name}", code="unknown_tag", details={"name": name})


def _change_json(entry: StatusEntry) -> dict[str, Any]:
    change = {"state": entry.state, "path": entry.path}
    if entry.previous_path is not None:
        change["previous_path"] = entry.previous_path
    return change


def _change_text(entry: StatusEntry) -> str:
    if entry.previous_path is None:
        return f"{entry.state:<8} {entry.path}"
    return f"{entry.state:<8} {entry.path} (was {entry.previous_path})"


def _deleted_branch_json(branch: DeletedBranch) -> dict[str, Any]:
    return {
        "id": branch.id,
        "name": branch.name,
        "comment": branch.comment,
        "created_at": branch.created_at,
        "deleted_at": branch.deleted_at,
    }


def _bud_json(bud: Bud) -> dict[str, Any]:
    return {
        "id": bud.id,
        "name": bud.name,
        "base_commit_id": bud.base_commit_id,
        "branch_name": bud.branch_name,
        "branch_id": bud.branch_id,
        "created_at": bud.created_at,
        "changes": [_change_json(entry) for entry in bud.changes],
        "files": [
            {
                "path": item.path,
                "object_hash": item.object_hash,
                "size": item.size,
                "mtime_ns": item.mtime_ns,
                "file_id": item.file_id,
            }
            for item in bud.files
        ],
    }


def _bud_summary(bud: Bud) -> str:
    base = bud.base_commit_id[:12] if bud.base_commit_id else "(no commit)"
    name = f' "{bud.name}"' if bud.name else ""
    return f"{bud.id[:12]}{name} on {base} [{bud.branch_name}] {len(bud.changes)} changes"


def _graph_json(graph: CommitGraph) -> dict[str, Any]:
    tip = next((branch.commit_id for branch in graph.branches if branch.current), None)
    return {
        "current_commit": graph.current_commit,
        "at_branch_tip": graph.current_commit == tip,
        "commits": [
            {
                "id": commit.id,
                "parent_id": commit.parent_id,
                "branch_name": commit.branch_name,
                "branch_id": commit.branch_id,
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
                "id": branch.id,
                "name": branch.name,
                "commit_id": branch.commit_id,
                "comment": branch.comment,
                "current": branch.current,
                "created_at": branch.created_at,
            }
            for branch in graph.branches
        ],
        "deleted_branches": [_deleted_branch_json(branch) for branch in graph.deleted_branches],
        "tags": [
            {
                "name": tag.name,
                "commit_id": tag.commit_id,
                "comment": tag.comment,
                "created_at": tag.created_at,
            }
            for tag in graph.tags
        ],
        "buds": [_bud_json(bud) for bud in graph.buds],
    }


def _prune_json(result: PruneResult) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "dry_run": result.dry_run,
        "start_tag": result.start_tag,
        "end_tag": result.end_tag,
        "removed_commits": [
            {
                "id": commit.id,
                "created_at": commit.created_at,
                "message": commit.message,
            }
            for commit in result.commits
        ],
        "reclaimable_objects": list(result.reclaimable_objects),
        "reclaimable_bytes": result.reclaimable_bytes,
    }


def _delete_commit_json(result: CommitDeletion) -> dict[str, Any]:
    return {
        "dry_run": result.dry_run,
        "commit": {
            "id": result.commit.id,
            "created_at": result.commit.created_at,
            "message": result.commit.message,
        },
        "parent_id": result.parent_id,
        "moved_branches": [
            {"id": branch.id, "name": branch.name, "current": branch.current}
            for branch in result.moved_branches
        ],
        "moved_current": result.moved_current,
        "reconnected_children": list(result.reconnected_children),
        "rebased_buds": list(result.rebased_buds),
        "reclaimable_objects": list(result.reclaimable_objects),
        "reclaimable_bytes": result.reclaimable_bytes,
    }


def _tree_text_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def _tree_commit_text(
    commit: GraphCommit,
    branches_by_commit: dict[str, list[str]],
    tags_by_commit: dict[str, list[str]],
    current_commit: str | None = None,
) -> str:
    markers = [f"created:{commit.branch_name}"]
    if commit.id == current_commit:
        markers.append("current")
    markers.extend(
        f"branch:{branch}" for branch in branches_by_commit.get(commit.id, [])
    )
    markers.extend(f"tag:{tag}" for tag in tags_by_commit.get(commit.id, []))
    preview_count = 0
    for attachment in commit.attachments:
        if attachment.role == "thumbnail":
            markers.append("thumbnail")
        elif attachment.role == "preview":
            preview_count += 1
        else:
            markers.append(f"attachment:{attachment.role}")
    if preview_count:
        markers.append(f"previews:{preview_count}")
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
    # The graph lists commits newest first by their creation sequence.
    creation_order = {commit.id: -index for index, commit in enumerate(graph.commits)}
    for items in children.values():
        items.sort(key=lambda item: creation_order[item.id])

    lines: list[str] = []
    for root in children.get(None, []):
        text = _tree_commit_text(
            root, branches_by_commit, tags_by_commit, graph.current_commit
        )
        lines.append(f"* {text}")
        root_children = children.get(root.id, [])
        stack: list[tuple[GraphCommit, str, bool]] = [
            (child, "", index == len(root_children) - 1)
            for index, child in reversed(list(enumerate(root_children)))
        ]
        while stack:
            commit, prefix, is_last = stack.pop()
            connector = "`- " if is_last else "|- "
            text = _tree_commit_text(
                commit, branches_by_commit, tags_by_commit, graph.current_commit
            )
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


def _echo_branch_position(
    branch_name: str, current_commit: str | None, at_branch_tip: bool
) -> None:
    typer.echo(f"On branch {branch_name}")
    if current_commit is not None and not at_branch_tip:
        typer.echo(f"Viewing saved snapshot {current_commit[:12]} (not the branch tip)")


@app.command()
def status(
    paths: Annotated[list[Path] | None, typer.Argument(help="Paths whose tracking state should be checked")] = None,
    tracked: Annotated[bool, typer.Option("--tracked", help="List every tracked file")] = False,
    untracked: Annotated[bool, typer.Option("--untracked", help="List every untracked file")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """Show changes or whether specific paths are tracked."""
    repository = repo()
    head = repository.head_position()
    branch_name = head.branch
    current_commit, at_branch_tip = head.current_commit, head.at_branch_tip
    position = {
        "branch_id": head.branch_id,
        "current_commit": current_commit,
        "at_branch_tip": at_branch_tip,
    }
    if paths:
        if tracked or untracked:
            raise SproutError("path status cannot be combined with --tracked or --untracked")
        path_entries = repository.tracking_status(paths)
        if json_output:
            _echo_json(
                {
                    "branch": branch_name,
                    **position,
                    "paths": [
                        {"path": path, "tracked": is_tracked}
                        for path, is_tracked in path_entries
                    ],
                }
            )
            return
        _echo_branch_position(branch_name, current_commit, at_branch_tip)
        for path, is_tracked in path_entries:
            typer.echo(f"{'tracked' if is_tracked else 'untracked':<9} {path}")
        return
    with _show_progress(repository, enabled=not json_output):
        entries = repository.status()
    if json_output:
        payload: dict[str, Any] = {
            "branch": branch_name,
            **position,
            "changes": [_change_json(entry) for entry in entries],
        }
        if tracked:
            payload["tracked"] = sorted(repository.tracked())
            cover_id, cover_path = repository.cover_file()
            if cover_id is not None:
                payload["cover"] = {"file_id": cover_id, "path": cover_path}
        if untracked:
            payload["untracked"] = repository.untracked_files()
        _echo_json(payload)
        return
    _echo_branch_position(branch_name, current_commit, at_branch_tip)
    if not entries:
        typer.echo("Working tree clean")
    for entry in entries:
        typer.echo(_change_text(entry))
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


@leaf_app.command(name="create")
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
                "branch": result.branch,
                "branch_id": result.branch_id,
                "created_branch": result.created_branch,
                "message": message.strip(),
                "removed_paths": list(result.removed_paths),
                **(
                    {"cover": {"applied": result.cover.applied, "reason": result.cover.reason}}
                    if result.cover is not None
                    else {}
                ),
            }
        )
        return
    for path in result.removed_paths:
        typer.echo(f"deleted  {path}")
    if result.cover is not None and not result.cover.applied:
        typer.echo(f"Warning: no thumbnail from the cover file: {result.cover.reason}", err=True)
    if result.created_branch:
        typer.echo(f"Created branch {result.branch} from a snapshot that is not a branch tip")
    typer.echo(f"[{result.branch} {result.commit_id[:12]}] {message.strip()}")


@app.command(name="cover")
def cover_command(
    path: Annotated[
        Path | None, typer.Argument(help="Tracked image to make thumbnails from; omit to inspect")
    ] = None,
    clear: Annotated[bool, typer.Option("--clear", help="Stop making thumbnails from a cover file")] = False,
    apply: Annotated[
        bool, typer.Option("--apply", help="Give existing leaves without a thumbnail one from the cover")
    ] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="With --apply, report without saving")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """Inspect, set, clear, or apply the file that thumbnails are made from."""
    if sum((path is not None, clear, apply)) > 1:
        raise SproutError("use only one of PATH, --clear, or --apply")
    if dry_run and not apply:
        raise SproutError("--dry-run is only used with --apply")
    repository = repo()
    if apply:
        result = repository.apply_cover(dry_run=dry_run)
        if json_output:
            _echo_json(result)
            return
        action = "Would add" if dry_run else "Added"
        typer.echo(
            f"{action} {len(result['applied'])} thumbnail(s); kept {result['kept']}; skipped {len(result['skipped'])}"
        )
        return
    if clear:
        repository.clear_cover()
        if json_output:
            _echo_json({"file_id": None, "path": None})
            return
        typer.echo("Cleared the cover file")
        return
    if path is not None:
        file_id, relative, problem = repository.set_cover(path)
        if json_output:
            _echo_json({"file_id": file_id, "path": relative, "problem": problem})
            return
        typer.echo(f"Set the cover file to {relative}")
        if problem is not None:
            typer.echo(f"Warning: it cannot make a thumbnail now: {problem}", err=True)
        return
    file_id, relative = repository.cover_file()
    if json_output:
        _echo_json({"file_id": file_id, "path": relative})
        return
    if file_id is None:
        typer.echo("No cover file")
    else:
        typer.echo(relative if relative is not None else f"{file_id} (no longer tracked)")


@app.command(name="file-history")
def file_history(
    file_id: Annotated[str, typer.Argument(help="Immutable file ID from show --json")],
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List snapshots and paths of one material across renames and branches."""
    rows = repo().file_history(file_id)
    if json_output:
        _echo_json(rows)
    else:
        for row in rows:
            typer.echo(f"{row['commit_id']}  {row['path']}  {row['message']}")


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


@leaf_app.command(name="tree")
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
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Show file-level differences between commits or the working tree."""
    repository = repo()
    with _show_progress(repository):
        entries = repository.diff(commit_a, commit_b)
    if json_output:
        _echo_json([
            {
                "state": entry.state,
                "path": entry.path,
                "old_size": entry.old_size,
                "new_size": entry.new_size,
                **({"previous_path": entry.previous_path} if entry.previous_path is not None else {}),
            }
            for entry in entries
        ])
        return
    if not entries:
        typer.echo("No differences")
        return
    for entry in entries:
        if entry.state == "renamed":
            typer.echo(f"{entry.state:<8} {entry.path} (was {entry.previous_path})")
        elif entry.state == "modified" and entry.old_size is not None and entry.new_size is not None:
            typer.echo(
                f"{entry.state:<8} {entry.path}  ({entry.old_size} bytes -> {entry.new_size} bytes)"
            )
        elif entry.state == "added" and entry.new_size is not None:
            typer.echo(f"{entry.state:<8} {entry.path}  ({entry.new_size} bytes)")
        elif entry.state == "deleted" and entry.old_size is not None:
            typer.echo(f"{entry.state:<8} {entry.path}  ({entry.old_size} bytes)")
        else:
            typer.echo(f"{entry.state:<8} {entry.path}")


@leaf_app.command(name="show")
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
    attachments = repository.attachments_many([row["id"]])[row["id"]]
    if json_output:
        if timezone_name.upper() != "UTC":
            raise SproutError("--timezone cannot be used with --json")
        _echo_json(_show_json(row, files, thumbnail, annotations, attachments))
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
    previews = [item for item in attachments if item.role == "preview"]
    for index, attachment in enumerate(previews, start=1):
        typer.echo(f"Preview {_preview_text(index, attachment)}")
    for attachment in attachments:
        if attachment.role not in {"thumbnail", "preview"}:
            typer.echo(
                f"Attachment: {attachment.id} [{attachment.role}:{attachment.position}] "
                f"{attachment.original_name} ({attachment.media_type}, {attachment.size} bytes)"
            )
    for item in files:
        modified_at = datetime.fromtimestamp(item.mtime_ns // 1_000_000_000, tz=timezone.utc)
        typer.echo(
            f"{item.object_hash[:12]}  {item.size:>10}  "
            f"{_format_datetime(modified_at, display_timezone)}  {item.path}"
        )


@app.command()
def message(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    text: Annotated[str, typer.Argument(help="New commit message")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Replace a commit message without changing the snapshot."""
    commit_id, normalized = repo().set_message(commit, text)
    if json_output:
        _echo_json({"commit_id": commit_id, "message": normalized})
        return
    typer.echo(f"Updated message for {commit_id[:12]}: {normalized}")


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


preview_app = typer.Typer(
    help="List, add, replace, delete, export, or reorder commit previews.",
    no_args_is_help=True,
)
app.add_typer(preview_app, name="preview")

PreviewCommitArgument = Annotated[
    str,
    typer.Argument(
        help="Commit ID, prefix, branch, or tag",
        autocompletion=_complete_references,
    ),
]
PreviewIdArgument = Annotated[
    str, typer.Argument(help="Preview attachment ID or unique prefix")
]
PreviewMediaTypeOption = Annotated[
    str | None,
    typer.Option(
        "--media-type",
        help="Media type to record instead of guessing from the file name",
    ),
]
PreviewYesOption = Annotated[
    bool,
    typer.Option("--yes", "-y", help="Confirm registering large preview files"),
]
PreviewDryRunOption = Annotated[
    bool,
    typer.Option("--dry-run", help="Show size and storage impact without saving"),
]
PreviewJsonOption = Annotated[
    bool, typer.Option("--json", help="Output structured preview metadata")
]


def _preview_plan_json(plan: PreviewPlan) -> dict[str, Any]:
    return {
        "source": plan.source,
        "original_name": plan.original_name,
        "media_type": plan.media_type,
        "size": plan.size,
        "object_hash": plan.object_hash,
        "already_stored": plan.already_stored,
        "additional_bytes": plan.additional_bytes,
        "requires_confirmation": plan.requires_confirmation,
    }


def _echo_preview_plans(plans: list[PreviewPlan], json_output: bool) -> None:
    if json_output:
        _echo_json(
            {
                "previews": [_preview_plan_json(plan) for plan in plans],
                "additional_bytes": sum(plan.additional_bytes for plan in plans),
                "requires_confirmation": any(
                    plan.requires_confirmation for plan in plans
                ),
            }
        )
        return
    for plan in plans:
        stored = "already stored" if plan.already_stored else f"+{plan.additional_bytes} bytes"
        warning = "  [needs --yes]" if plan.requires_confirmation else ""
        typer.echo(
            f"{plan.original_name}  {plan.media_type}  {plan.size} bytes  ({stored}){warning}"
        )
    typer.echo(
        f"Up to {sum(plan.additional_bytes for plan in plans)} bytes before compression"
    )


def _preview_text(index: int, attachment: CommitAttachment) -> str:
    return (
        f"{index}. {attachment.id}  {attachment.original_name} "
        f"({attachment.media_type}, {attachment.size} bytes)"
    )


@preview_app.command(name="list")
def preview_list(
    commit: PreviewCommitArgument,
    json_output: PreviewJsonOption = False,
) -> None:
    """List previews in their saved display order."""
    previews = repo().previews(commit)
    if json_output:
        _echo_json([_attachment_json(item) for item in previews])
        return
    if not previews:
        typer.echo("No previews")
        return
    for index, item in enumerate(previews, start=1):
        typer.echo(_preview_text(index, item))
        typer.echo(f"   Created: {item.created_at}  Updated: {item.updated_at}")


@preview_app.command(name="image")
def preview_image(
    commit: PreviewCommitArgument,
    attachment_id: PreviewIdArgument,
    json_output: PreviewJsonOption = False,
) -> None:
    """Return a bounded static PNG rendering of a preview for the GUI."""
    from .preview_image import render_preview_image

    result = render_preview_image(repo(), commit, attachment_id)
    if json_output:
        _echo_json(result)
    else:
        typer.echo(result["data_url"])


@preview_app.command(name="add")
def preview_add(
    commit: PreviewCommitArgument,
    files: Annotated[
        list[Path], typer.Argument(help="Files of any format to append as previews")
    ],
    media_type: PreviewMediaTypeOption = None,
    yes: PreviewYesOption = False,
    dry_run: PreviewDryRunOption = False,
    json_output: PreviewJsonOption = False,
) -> None:
    """Append previews after the existing ones; all files are added or none are."""
    repository = repo()
    if dry_run:
        repository.resolve_commit(commit)
        _echo_preview_plans(repository.plan_previews(files, media_type), json_output)
        return
    with _show_progress(repository, enabled=not json_output):
        added = repository.add_previews(
            commit, files, media_type=media_type, confirm_large=yes
        )
    if json_output:
        _echo_json([_attachment_json(item) for item in added])
        return
    for item in added:
        typer.echo(f"Added preview {_preview_text(item.position + 1, item)}")


@preview_app.command(name="metadata")
def preview_metadata(
    commit: PreviewCommitArgument,
    attachment_id: PreviewIdArgument,
    name: Annotated[str | None, typer.Option("--name")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    material: Annotated[list[str] | None, typer.Option("--file-id")] = None,
    clear_materials: Annotated[bool, typer.Option("--clear-materials")] = False,
    json_output: PreviewJsonOption = False,
) -> None:
    """Edit preview presentation and same-snapshot material associations."""
    if material and clear_materials:
        raise SproutError('--file-id cannot be combined with --clear-materials')
    attachment = repo().set_preview_metadata(commit,attachment_id,
        display_name=name if name is not None else UNCHANGED,
        description=description if description is not None else UNCHANGED,
        file_ids=[] if clear_materials else material if material is not None else UNCHANGED)
    if json_output:
        _echo_json(_attachment_json(attachment))
    else:
        typer.echo(f'Updated preview metadata {attachment.id}')


@preview_app.command(name="replace")
def preview_replace(
    commit: PreviewCommitArgument,
    attachment_id: PreviewIdArgument,
    file: Annotated[Path, typer.Argument(help="New preview file of any format")],
    media_type: PreviewMediaTypeOption = None,
    yes: PreviewYesOption = False,
    dry_run: PreviewDryRunOption = False,
    json_output: PreviewJsonOption = False,
) -> None:
    """Replace one preview's content, keeping its ID and position."""
    repository = repo()
    if dry_run:
        repository.preview(commit, attachment_id)
        _echo_preview_plans(repository.plan_previews([file], media_type), json_output)
        return
    with _show_progress(repository, enabled=not json_output):
        attachment = repository.replace_preview(
            commit, attachment_id, file, media_type=media_type, confirm_large=yes
        )
    if json_output:
        _echo_json(_attachment_json(attachment))
        return
    typer.echo(f"Replaced preview {_preview_text(attachment.position + 1, attachment)}; previous version retained in 'sprout trash'")


@preview_app.command(name="delete")
def preview_delete(
    commit: PreviewCommitArgument,
    attachment_id: PreviewIdArgument,
    json_output: PreviewJsonOption = False,
) -> None:
    """Delete one preview; the remaining previews keep their relative order."""
    attachment = repo().delete_preview(commit, attachment_id)
    if json_output:
        _echo_json({**_attachment_json(attachment), "deleted": True})
        return
    typer.echo(
        f"Deleted preview {attachment.id} ({attachment.original_name}) "
        f"from {attachment.commit_id[:12]}; recover with 'sprout trash' before changing previews"
    )


@preview_app.command(name="export")
def preview_export(
    commit: PreviewCommitArgument,
    attachment_id: PreviewIdArgument,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Write the preview to this file"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite an existing output file"),
    ] = False,
    json_output: PreviewJsonOption = False,
) -> None:
    """Write one preview's original content to a file outside the tracked files."""
    repository = repo()
    with _show_progress(repository, enabled=not json_output):
        destination = repository.export_preview(
            commit, attachment_id, output, force=force
        )
    if json_output:
        _echo_json({"output": str(destination)})
        return
    typer.echo(f"Exported preview to {destination}")


@preview_app.command(name="order")
def preview_order(
    commit: PreviewCommitArgument,
    attachment_ids: Annotated[
        list[str],
        typer.Argument(help="Every preview ID of the commit in the new display order"),
    ],
    json_output: PreviewJsonOption = False,
) -> None:
    """Save a new display order for all previews of a commit."""
    previews = repo().reorder_previews(commit, attachment_ids)
    if json_output:
        _echo_json([_attachment_json(item) for item in previews])
        return
    for index, item in enumerate(previews, start=1):
        typer.echo(_preview_text(index, item))


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
            typer.echo(f"Deleted note from {annotations.commit_id[:12]}; recover it with 'sprout trash'")
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
    keep_changes: Annotated[
        bool,
        typer.Option(
            "--keep-changes",
            help="With --switch, keep unsaved changes as a bud instead of refusing",
        ),
    ] = False,
    deleted: Annotated[
        bool, typer.Option("--deleted", help="List deleted branches and when they were deleted")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """List, create, delete, rename, or edit a branch."""
    repository = repo()
    if deleted:
        if (
            name is not None
            or start_point is not None
            or comment
            or set_comment is not None
            or delete is not None
            or rename is not None
            or switch
        ):
            raise SproutError("--deleted cannot be combined with other branch operations")
        branches = repository.deleted_branches()
        if json_output:
            _echo_json([_deleted_branch_json(item) for item in branches])
            return
        if not branches:
            typer.echo("No deleted branches")
            return
        for item in branches:
            typer.echo(f"{item.name:<20} {item.id[:12]}  created {item.created_at}  deleted {item.deleted_at}")
        return
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
        branch_id = repository.delete_branch(delete)
        if json_output:
            _echo_json({"id": branch_id, "name": delete, "deleted": True})
            return
        typer.echo(f"Deleted branch {delete}; recover it with 'sprout trash'")
        return
    if rename is not None:
        if name is None:
            raise SproutError("a branch name is required with --rename")
        if start_point is not None or comment or set_comment is not None or switch:
            raise SproutError("--rename cannot be combined with comment options")
        branch_id = repository.rename_branch(name, rename)
        if json_output:
            _echo_json({"id": branch_id, "name": rename, "previous_name": name})
            return
        typer.echo(f"Renamed branch {name} to {rename}")
        return
    if set_comment is not None:
        if name is None:
            raise SproutError("a branch name is required with --set-comment")
        if start_point is not None or comment or switch:
            raise SproutError("--comment and --set-comment cannot be used together")
        branch_id = repository.set_branch_comment(name, set_comment)
        if json_output:
            _echo_json({"id": branch_id, "name": name, "comment": set_comment.strip()})
            return
        typer.echo(f"Updated comment for branch {name}")
        return
    if keep_changes and (name is None or not switch):
        raise SproutError("--keep-changes requires a branch name and --switch")
    if keep_changes:
        with _show_progress(repository, enabled=not json_output):
            commit_id, stashed = repository.grow_branch(name, comment, start_point=start_point)
        if json_output:
            _echo_json(
                {
                    "id": repository.branch_id(name),
                    "name": name,
                    "commit_id": commit_id,
                    "comment": comment.strip(),
                    "current": True,
                    "bud": _bud_json(stashed) if stashed is not None else None,
                }
            )
            return
        if stashed is not None:
            typer.echo(f"Saved bud {_bud_summary(stashed)}")
        typer.echo(f"Created and switched to branch {name}")
        return
    if name is not None:
        with _show_progress(repository, enabled=not json_output):
            commit_id = repository.create_branch(
                name, comment, start_point=start_point, switch=switch
            )
        if json_output:
            _echo_json(
                {
                    "id": repository.branch_id(name),
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
    set_comment: Annotated[
        str | None, typer.Option("--set-comment", help="Replace an existing tag comment")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """List, create, delete, or edit tags."""
    repository = repo()
    if delete is not None:
        if name is not None or commit is not None or comment or set_comment is not None:
            raise SproutError("--delete cannot be combined with tag creation arguments")
        repository.delete_tag(delete)
        if json_output:
            _echo_json({"name": delete, "deleted": True})
            return
        typer.echo(f"Deleted tag {delete}; recover it with 'sprout trash'")
        return
    if set_comment is not None:
        if name is None:
            raise SproutError("a tag name is required with --set-comment")
        if commit is not None or comment:
            raise SproutError("--comment and --set-comment cannot be used together")
        repository.set_tag_comment(name, set_comment)
        if json_output:
            _echo_json(_tag_json(repository, name))
            return
        typer.echo(f"Updated comment for tag {name}")
        return
    if name is not None:
        commit_id = repository.create_tag(name, commit, comment)
        if json_output:
            _echo_json(_tag_json(repository, name))
            return
        typer.echo(f"Created tag {name} at {commit_id[:12]}")
        return
    if commit is not None or comment:
        raise SproutError("a tag name is required")
    tags = repository.tags()
    if json_output:
        _echo_json(
            [
                {"name": tag_name, "commit_id": commit_id, "comment": tag_comment, "created_at": created_at}
                for tag_name, commit_id, tag_comment, created_at in tags
            ]
        )
        return
    if not tags:
        typer.echo("No tags")
        return
    for tag_name, commit_id, tag_comment, _created_at in tags:
        suffix = f"  # {tag_comment}" if tag_comment else ""
        typer.echo(f"{tag_name:<20} {commit_id[:12]}{suffix}")


@app.command()
def bud(
    save: Annotated[
        bool,
        typer.Option(
            "--save",
            help="Move unsaved tracked changes into a new bud and return the files to the current snapshot",
        ),
    ] = False,
    keep_files: Annotated[
        bool,
        typer.Option("--keep-files", help="With --save, copy the changes and leave the working files as they are"),
    ] = False,
    name: Annotated[
        str, typer.Option("--name", help="Name for the bud created with --save")
    ] = "",
    rename: Annotated[
        tuple[str, str] | None,
        typer.Option("--rename", help="Set a bud's name: --rename BUD NAME (empty NAME clears it)"),
    ] = None,
    restore: Annotated[
        str | None,
        typer.Option("--restore", help="Bring a bud back into the working tree"),
    ] = None,
    drop: Annotated[
        str | None, typer.Option("--drop", help="Move a bud to the trash")
    ] = None,
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirm moving a bud to the trash with --drop")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """List, save, restore, or drop buds of unsaved changes."""
    if sum((save, restore is not None, drop is not None, rename is not None)) > 1:
        raise SproutError("use only one of --save, --restore, --drop, or --rename")
    if name and not save:
        raise SproutError("--name is only used with --save")
    if keep_files and not save:
        raise SproutError("--keep-files is only used with --save")
    repository = repo()
    if rename is not None:
        renamed = repository.rename_bud(*rename)
        if json_output:
            _echo_json(_bud_json(renamed))
            return
        typer.echo(f"Renamed bud {_bud_summary(renamed)}")
        return
    if save:
        with _show_progress(repository, enabled=not json_output):
            saved = repository.save_bud(name) if keep_files else repository.move_changes_to_bud(name)
        if json_output:
            _echo_json(_bud_json(saved))
            return
        if keep_files:
            typer.echo(f"Saved bud {_bud_summary(saved)}; working files unchanged")
        else:
            typer.echo(f"Moved unsaved changes to bud {_bud_summary(saved)}")
        return
    if restore is not None:
        with _show_progress(repository, enabled=not json_output):
            restored, stashed = repository.restore_bud(restore)
        if json_output:
            _echo_json(
                {
                    "restored": _bud_json(restored),
                    "saved": _bud_json(stashed) if stashed is not None else None,
                }
            )
            return
        if stashed is not None:
            typer.echo(f"Saved bud {_bud_summary(stashed)}")
        typer.echo(f"Restored bud {_bud_summary(restored)}")
        return
    if drop is not None:
        if not yes:
            raise SproutError("dropping a bud moves it to the trash; rerun with --yes")
        dropped = repository.drop_bud(drop)
        if json_output:
            _echo_json(_bud_json(dropped))
            return
        typer.echo(f"Dropped bud {_bud_summary(dropped)}; recover it with 'sprout trash'")
        return
    if yes:
        raise SproutError("--yes is only used with --drop")
    buds = repository.buds()
    if json_output:
        _echo_json([_bud_json(item) for item in buds])
        return
    if not buds:
        typer.echo("No buds")
        return
    for item in buds:
        typer.echo(_bud_summary(item))


@app.command()
def go(
    target: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag to move to",
            autocompletion=_complete_references,
        ),
    ],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Move to a snapshot, keeping unsaved changes as a bud."""
    repository = repo()
    with _show_progress(repository, enabled=not json_output):
        result = repository.go(target)
    if json_output:
        _echo_json(
            {
                "current_commit": result.commit_id,
                "branch": result.branch,
                "branch_id": result.branch_id,
                "at_branch_tip": result.at_branch_tip,
                "bud": _bud_json(result.bud) if result.bud is not None else None,
                "changes": [_change_json(entry) for entry in result.changes],
            }
        )
        return
    if result.bud is not None:
        typer.echo(f"Saved bud {_bud_summary(result.bud)}")
    where = "branch tip" if result.at_branch_tip else "saved snapshot"
    typer.echo(f"Moved to {where} {result.commit_id[:12]} on {result.branch}")


@app.command(name="switch")
def switch_command(
    branch_name: Annotated[
        str, typer.Argument(autocompletion=_complete_branches)
    ],
    discard: Annotated[
        bool,
        typer.Option(
            "--discard",
            help="Discard all tracked changes, keeping them in the trash; leave untracked files untouched",
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
        _echo_json(
            {
                "branch": branch_name,
                "branch_id": repository.branch_id(),
                "commit_id": commit_id,
            }
        )
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
            help="Discard tracked changes on restored paths, keeping them in the trash; leave other files untouched",
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
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Write files from a commit without changing the working tree."""
    repository = repo()
    with _show_progress(repository, enabled=not json_output):
        result = repository.export(commit, output, paths, force=force)
    if json_output:
        _echo_json(
            {
                "commit_id": result.commit_id,
                "output": str(output.resolve()),
                "paths": list(result.paths),
            }
        )
        return
    for path in result.paths:
        typer.echo(f"export  {path}")
    typer.echo(
        f"Exported {len(result.paths)} file(s) from {result.commit_id[:12]} "
        f"to {output.resolve()}"
    )


def _archive_plan_json(plan: ArchivePlan, *, dry_run: bool) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "output": str(plan.output),
        "commits": plan.commits,
        "files": plan.files,
        "estimated_bytes": plan.bytes,
        "free_bytes": plan.free_bytes,
        "sufficient_space": plan.sufficient_space,
        "removes_incomplete": plan.removes_incomplete,
    }


@leaf_app.command(name="archive")
@app.command(name="archive")
def archive_command(
    output: Annotated[
        Path,
        typer.Option(
            "--output", "-o", help="New or empty directory to write the static archive"
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show counts, estimated size and free space without writing",
        ),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Expand every commit into static HTML, JSON and plain files."""
    repository = repo()
    if dry_run:
        plan = repository.plan_archive(output)
    else:
        with _show_progress(repository, enabled=not json_output):
            plan = repository.archive(output)
    if json_output:
        _echo_json(_archive_plan_json(plan, dry_run=dry_run))
        return
    typer.echo(f"Commits:         {plan.commits}")
    typer.echo(f"Files:           {plan.files}")
    typer.echo(f"Estimated size:  {plan.bytes} bytes")
    typer.echo(f"Free space:      {plan.free_bytes} bytes")
    if plan.removes_incomplete:
        typer.echo(f"Incomplete archive to replace: {plan.staging}")
    if dry_run:
        if not plan.sufficient_space:
            typer.echo("Not enough free space for this archive")
            raise typer.Exit(1)
        typer.echo(f"Would archive {plan.commits} commit(s) to {plan.output}")
        return
    typer.echo(f"Archived {plan.commits} commit(s) to {plan.output}")


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


@leaf_app.command(name="prune")
@app.command()
def prune(
    start_tag: Annotated[
        str | None,
        typer.Argument(help="Older boundary tag; omit when using --all"),
    ] = None,
    end_tag: Annotated[
        str | None,
        typer.Argument(help="Newer boundary tag; omit when using --all"),
    ] = None,
    all_history: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Keep only tagged commits and existing branch tips across all history",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show commits and reclaimable objects without changing history",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm the irreversible history change"),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Delete unprotected intermediate commits and reconnect retained history."""
    if all_history and (start_tag is not None or end_tag is not None):
        raise SproutError("--all cannot be combined with tag arguments")
    if not all_history and (start_tag is None or end_tag is None):
        raise SproutError("specify START_TAG END_TAG or --all")
    if not dry_run and not yes:
        raise SproutError(
            "prune is irreversible; review --dry-run, then rerun with --yes"
        )

    result = repo().prune(
        start_tag,
        end_tag,
        all_history=all_history,
        dry_run=dry_run,
    )
    if json_output:
        _echo_json(_prune_json(result))
        return
    for commit in result.commits:
        typer.echo(f"commit  {commit.id[:12]} {commit.message}")
    action = "Would remove" if dry_run else "Removed"
    typer.echo(
        f"{action} {len(result.commits)} commits; "
        f"{len(result.reclaimable_objects)} objects "
        f"({result.reclaimable_bytes} bytes) become reclaimable"
    )
    if not dry_run and result.reclaimable_objects:
        typer.echo("Run 'sprout gc' to reclaim object storage")


@app.command(name="trash")
def trash(
    action: Annotated[str, typer.Argument(help="list, show, restore, or purge")] = "list",
    item_id: Annotated[str | None, typer.Argument(help="Exact trash item ID")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Inspect without applying changes")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm permanent deletion of the recovery record")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output structured JSON")] = False,
) -> None:
    """Inspect recovery items, restore metadata, or permanently discard recovery data."""
    if action not in {"list", "show", "restore", "purge"}:
        raise SproutError("trash action must be list, show, restore, or purge")
    if (action == "list" and item_id is not None) or (action != "list" and item_id is None):
        raise SproutError("list takes no ID; show, restore and purge require an exact trash ID")
    repository = repo()
    if action == "list":
        result = repository.trash_items()
    elif action == "show":
        result = repository.trash_detail(item_id)
    elif action == "restore":
        result = repository.restore_trash(item_id, dry_run=dry_run)
    else:
        if not dry_run and not yes:
            raise SproutError("permanent deletion is irreversible; review trash purge ID --dry-run, then use --yes",
                              code="trash_confirmation_required", details={"trash_id": item_id})
        result = repository.purge_trash(item_id, dry_run=dry_run)
    if json_output:
        _echo_json(result)
        return
    entries = result if isinstance(result, list) else [result]
    for entry in entries:
        typer.echo(f"{entry['id']}  {entry['kind']}  {entry['title']}  {entry['created_at']}")
        typer.echo(f"  protected {entry['protected_bytes']} bytes; reclaimable after purge {entry['reclaimable_bytes']} bytes")
    if not entries:
        typer.echo("Trash is empty")
    if action == "restore":
        typer.echo("Restore checked; no changes applied" if dry_run else "Restored; working files unchanged")
    if action == "purge":
        typer.echo("Would permanently discard recovery; run gc afterwards to reclaim objects" if dry_run else
                   "Permanently discarded recovery; run gc to reclaim unreferenced objects")


@leaf_app.command(name="delete")
@app.command(name="delete-commit")
def delete_commit(
    commit: Annotated[
        str,
        typer.Argument(
            help="Commit ID, prefix, branch, or tag",
            autocompletion=_complete_references,
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would change without deleting"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Confirm moving this commit to trash"),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Delete one untagged commit and move its references to its parent."""
    if not dry_run and not yes:
        raise SproutError(
            "delete-commit moves references and saves recovery data in trash; review --dry-run, then rerun with --yes"
        )
    result = repo().delete_commit(commit, dry_run=dry_run)
    if json_output:
        _echo_json(_delete_commit_json(result))
        return
    parent = result.parent_id[:12] if result.parent_id else "no commit"
    typer.echo(f"commit  {result.commit.id[:12]} {result.commit.message}")
    for branch in result.moved_branches:
        typer.echo(f"branch  {branch.name} -> {parent}")
    if result.moved_current:
        typer.echo(
            f"current -> {parent} (working files are unchanged and stay as unsaved changes)"
        )
    if result.reconnected_children:
        typer.echo(f"children reconnected to {parent}: {len(result.reconnected_children)}")
    if result.rebased_buds:
        typer.echo(f"buds rebased onto {parent}: {len(result.rebased_buds)}")
    action = "Would delete" if dry_run else "Deleted"
    typer.echo(
        f"{action} commit {result.commit.id[:12]}; "
        f"{len(result.reclaimable_objects)} objects "
        f"({result.reclaimable_bytes} bytes) are retained in trash until permanently discarded"
    )
    if not dry_run and result.reclaimable_objects:
        typer.echo("Use 'sprout trash' to inspect recovery data; gc keeps it until permanent deletion")


@app.command()
def gc(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List reclaimable objects without deleting them"),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Delete unreferenced objects and leftover temporary object files."""
    result = repo().gc(dry_run=dry_run)
    if json_output:
        _echo_json(
            {
                "dry_run": result.dry_run,
                "removed_objects": result.removed_objects,
                "removed_temps": result.removed_temps,
                "freed_bytes": result.freed_bytes,
                "objects": list(result.objects),
                "temps": list(result.temps),
            }
        )
        return
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
def serve() -> None:
    """Answer JSON Lines requests on stdin without restarting (for the GUI)."""
    from .serve import serve as serve_requests

    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    serve_requests(app, __version__)


@app.command()
def doctor(
    report: Annotated[
        bool, typer.Option("--report", help="Exit successfully even when issues are found")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Inspect repository integrity without changing files."""
    result = repo().doctor()
    failure_code = 0 if report else 1
    if json_output:
        _echo_json(
            {
                "ok": result.ok,
                "checked_objects": result.checked_objects,
                "issues": [
                    {"kind": issue.kind, "detail": issue.detail} for issue in result.issues
                ],
            }
        )
        if not result.ok:
            raise typer.Exit(failure_code)
        return
    for issue in result.issues:
        typer.echo(f"{issue.kind:<18} {issue.detail}")
    if result.ok:
        typer.echo(f"OK ({result.checked_objects} objects checked)")
        return
    typer.echo(
        f"Found {len(result.issues)} issue(s) ({result.checked_objects} objects checked)"
    )
    raise typer.Exit(failure_code)


@app.command()
def stats(
    json_output: Annotated[
        bool, typer.Option("--json", help="Output structured JSON")
    ] = False,
) -> None:
    """Show repository size and basic counts."""
    result = repo().stats()
    if json_output:
        _echo_json(
            {
                "commits": result.commits,
                "branches": result.branches,
                "tracked_paths": result.tracked_paths,
                "buds": result.buds,
                "objects": result.objects,
                "objects_bytes": result.objects_bytes,
                "logical_bytes": result.logical_bytes,
                "unique_bytes": result.unique_bytes,
                "dedup_saved_bytes": result.dedup_saved_bytes,
            }
        )
        return
    typer.echo(f"Commits:       {result.commits}")
    typer.echo(f"Branches:      {result.branches}")
    typer.echo(f"Tracked paths: {result.tracked_paths}")
    typer.echo(f"Buds:          {result.buds}")
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
        exit_code = app(standalone_mode=False)
        if isinstance(exit_code, int):
            return exit_code
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
