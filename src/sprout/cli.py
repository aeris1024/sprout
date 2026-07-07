from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .errors import SproutError
from .repository import Repository

app = typer.Typer(no_args_is_help=True, help="Offline snapshot version control for local files.")


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


@app.command()
def init(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    """Initialize a Sprout project."""
    created = Repository.init(path)
    typer.echo(f"Initialized Sprout project in {created.root}")


@app.command()
def track(paths: Annotated[list[Path], typer.Argument(help="Files or directories to track")]) -> None:
    """Register files for future commits."""
    added = repo().track(paths)
    for path in added:
        typer.echo(f"track  {path}")


@app.command()
def untrack(paths: Annotated[list[Path], typer.Argument(help="Files or directories to stop tracking")]) -> None:
    """Stop tracking paths without deleting working files."""
    removed = repo().untrack(paths)
    for path in removed:
        typer.echo(f"untrack  {path}")


@app.command()
def status(
    paths: Annotated[list[Path] | None, typer.Argument(help="Paths whose tracking state should be checked")] = None,
    tracked: Annotated[bool, typer.Option("--tracked", help="List every tracked file")] = False,
    untracked: Annotated[bool, typer.Option("--untracked", help="List every untracked file")] = False,
) -> None:
    """Show changes or whether specific paths are tracked."""
    repository = repo()
    typer.echo(f"On branch {repository.head_branch()}")
    if paths:
        for path, is_tracked in repository.tracking_status(paths):
            typer.echo(f"{'tracked' if is_tracked else 'untracked':<9} {path}")
        return
    entries = repository.status()
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
def commit_command(message: Annotated[str, typer.Option("--message", "-m")]) -> None:
    """Save a snapshot of all tracked files."""
    repository = repo()
    commit_id = repository.commit(message)
    typer.echo(f"[{repository.head_branch()} {commit_id[:12]}] {message.strip()}")


@app.command(name="log")
def log_command() -> None:
    """Show history of the current branch."""
    repository = repo()
    rows = repository.log()
    if not rows:
        typer.echo("No commits yet")
    for row in rows:
        typer.echo(f"commit {row['id']}")
        typer.echo(f"Date:   {row['created_at']}")
        typer.echo(f"\n    {row['message']}\n")


@app.command()
def show(commit: Annotated[str, typer.Argument(help="Commit ID, prefix, or branch")]) -> None:
    """Show a commit and its files."""
    row, files = repo().commit_info(commit)
    typer.echo(f"commit {row['id']}")
    typer.echo(f"Parent: {row['parent_id'] or '-'}")
    typer.echo(f"Branch: {row['branch_name']}")
    typer.echo(f"Date:   {row['created_at']}")
    typer.echo(f"\n    {row['message']}\n")
    for item in files:
        typer.echo(f"{item.object_hash[:12]}  {item.size:>10}  {item.mtime_ns}  {item.path}")


@app.command()
def branch(
    name: Annotated[str | None, typer.Argument()] = None,
    comment: Annotated[str, typer.Option("--comment", "-m", help="Comment for a new branch")] = "",
    set_comment: Annotated[
        str | None, typer.Option("--set-comment", help="Replace an existing branch comment")
    ] = None,
) -> None:
    """List branches, create one, or edit its comment."""
    repository = repo()
    if set_comment is not None:
        if name is None:
            raise SproutError("a branch name is required with --set-comment")
        if comment:
            raise SproutError("--comment and --set-comment cannot be used together")
        repository.set_branch_comment(name, set_comment)
        typer.echo(f"Updated comment for branch {name}")
        return
    if name is not None:
        repository.create_branch(name, comment)
        typer.echo(f"Created branch {name}")
        return
    if comment:
        raise SproutError("a branch name is required with --comment")
    current = repository.head_branch()
    for branch_name, commit_id, branch_comment in repository.branches():
        marker = "*" if branch_name == current else " "
        suffix = f"  # {branch_comment}" if branch_comment else ""
        typer.echo(f"{marker} {branch_name:<20} {(commit_id or '-')[:12]}{suffix}")


@app.command(name="switch")
def switch_command(
    branch_name: Annotated[str, typer.Argument()],
    discard: Annotated[bool, typer.Option("--discard", help="Discard tracked, uncommitted changes")] = False,
) -> None:
    """Switch to a branch and restore its tip."""
    repo().switch(branch_name, discard=discard)
    typer.echo(f"Switched to branch {branch_name}")


@app.command()
def restore(
    commit: Annotated[str, typer.Argument(help="Commit ID, prefix, or branch")],
    discard: Annotated[bool, typer.Option("--discard", help="Discard tracked, uncommitted changes")] = False,
) -> None:
    """Restore a snapshot without moving the branch tip."""
    commit_id = repo().restore(commit, discard=discard)
    typer.echo(f"Restored {commit_id[:12]} (branch tip unchanged)")


def main() -> int:
    try:
        app()
    except SproutError as exc:
        typer.echo(f"Error: {exc}", err=True)
        return 1
    except (OSError, sqlite3.Error) as exc:
        typer.echo(f"Error: repository operation failed: {exc}", err=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
