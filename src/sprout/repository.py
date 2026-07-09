from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

from .errors import SproutError

CONTROL_DIR = ".sprout"
DB_NAME = "repository.db"
SCHEMA_VERSION = "1"
HEX_BRANCH_NAME = re.compile(r"^[0-9a-f]{4,}$")
T = TypeVar("T")


def locked(method: Callable[..., T]) -> Callable[..., T]:
    """Serialize repository mutations across processes."""

    @wraps(method)
    def wrapper(self: Repository, *args: Any, **kwargs: Any) -> T:
        with self.lock():
            return method(self, *args, **kwargs)

    return wrapper


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commits (
    id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES commits(id),
    branch_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commit_files (
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    PRIMARY KEY (commit_id, path)
);
CREATE TABLE IF NOT EXISTS branches (
    name TEXT PRIMARY KEY,
    commit_id TEXT REFERENCES commits(id),
    comment TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS tracked_paths (
    path TEXT PRIMARY KEY
);
CREATE INDEX IF NOT EXISTS idx_commits_parent ON commits(parent_id);
"""


@dataclass(frozen=True)
class FileState:
    path: str
    object_hash: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class StatusEntry:
    state: str
    path: str


class Repository:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.control = self.root / CONTROL_DIR
        self.db_path = self.control / DB_NAME
        self.objects = self.control / "objects"
        self.tmp = self.control / "tmp"

    @classmethod
    def init(cls, path: Path) -> Repository:
        root = path.resolve()
        control = root / CONTROL_DIR
        root.mkdir(parents=True, exist_ok=True)
        try:
            # Directory creation is the atomic claim that prevents concurrent init.
            control.mkdir()
        except FileExistsError as exc:
            raise SproutError(f"already initialized: {root}") from exc
        repo = cls(root)
        try:
            repo.objects.mkdir()
            repo.tmp.mkdir()
            with repo.connect() as db:
                db.executescript(SCHEMA)
                db.execute("INSERT INTO meta(key, value) VALUES('schema_version', ?)", (SCHEMA_VERSION,))
                db.execute("INSERT INTO meta(key, value) VALUES('head_branch', 'main')")
                db.execute("INSERT INTO meta(key, value) VALUES('active_operation', '')")
                db.execute("INSERT INTO branches(name, commit_id, comment) VALUES('main', NULL, '')")
        except Exception:
            shutil.rmtree(control, ignore_errors=True)
            raise
        return repo

    @classmethod
    def discover(cls, start: Path | None = None) -> Repository:
        current = (start or Path.cwd()).resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if (candidate / CONTROL_DIR / DB_NAME).is_file():
                repo = cls(candidate)
                repo.check_schema()
                with repo.lock():
                    repo._recover_pending_materialization()
                return repo
        raise SproutError("not inside a Sprout project (run 'sprout init')")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA journal_mode = WAL")
            with db:
                yield db
        finally:
            db.close()

    def check_schema(self) -> None:
        try:
            with self.connect() as db:
                row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        except sqlite3.Error as exc:
            raise SproutError(f"cannot read repository: {exc}") from exc
        if row is None or row[0] != SCHEMA_VERSION:
            raise SproutError("unsupported repository schema version")

    @contextmanager
    def lock(self) -> Iterator[None]:
        """Acquire the single-writer repository lock without waiting."""
        lock_path = self.control / "lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise SproutError("another Sprout operation is already running") from exc
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def _relative_file(self, value: Path, *, must_exist: bool = True) -> str:
        absolute = value if value.is_absolute() else Path.cwd() / value
        absolute = absolute.resolve(strict=must_exist)
        try:
            relative = absolute.relative_to(self.root)
        except ValueError as exc:
            raise SproutError(f"path is outside the project: {value}") from exc
        if not relative.parts or relative.parts[0] == CONTROL_DIR:
            raise SproutError(f"cannot track Sprout metadata: {value}")
        return relative.as_posix()

    @locked
    def track(self, values: list[Path]) -> list[str]:
        paths: set[str] = set()
        for value in values:
            absolute = (value if value.is_absolute() else Path.cwd() / value)
            if absolute.is_symlink():
                raise SproutError(f"symbolic links are not supported: {value}")
            if absolute.is_dir():
                self._relative_file(absolute)
                for directory, dirs, files in os.walk(absolute, topdown=True, followlinks=False):
                    base = Path(directory)
                    dirs[:] = [
                        name
                        for name in dirs
                        if not (base / name).is_symlink()
                    ]
                    for name in files:
                        child = base / name
                        if child.is_symlink():
                            continue
                        relative = self._relative_file(child)
                        if CONTROL_DIR not in Path(relative).parts:
                            paths.add(relative)
            elif absolute.is_file():
                paths.add(self._relative_file(absolute))
            else:
                raise SproutError(f"file or directory does not exist: {value}")
        with self.connect() as db:
            db.executemany("INSERT OR IGNORE INTO tracked_paths(path) VALUES(?)", ((p,) for p in paths))
        return sorted(paths)

    @locked
    def untrack(self, values: list[Path]) -> list[str]:
        requested: list[str] = []
        with self.connect() as db:
            tracked = [row[0] for row in db.execute("SELECT path FROM tracked_paths")]
            for value in values:
                relative = self._relative_file(value, must_exist=False)
                prefix = relative.rstrip("/") + "/"
                requested.extend(p for p in tracked if p == relative or p.startswith(prefix))
            db.executemany("DELETE FROM tracked_paths WHERE path=?", ((p,) for p in set(requested)))
        return sorted(set(requested))

    @locked
    def move(self, source: Path, destination: Path) -> tuple[str, str]:
        source_input = source if source.is_absolute() else Path.cwd() / source
        if source_input.is_symlink():
            raise SproutError(f"symbolic links are not supported: {source}")
        if not source_input.exists():
            raise SproutError(f"file does not exist: {source}")
        source_relative = self._relative_file(source)
        tracked = self.tracked()
        if source_relative not in tracked:
            raise SproutError(f"path is not tracked: {source}")
        source_absolute = self.root / Path(source_relative)
        if not source_absolute.is_file():
            raise SproutError(f"tracked path is not a file: {source}")

        destination_relative = self._relative_file(destination, must_exist=False)
        destination_absolute = self.root / Path(destination_relative)
        if destination_absolute.exists():
            raise SproutError(f"destination already exists: {destination}")
        if destination_absolute.is_symlink():
            raise SproutError(f"symbolic links are not supported: {destination}")
        if destination_relative in tracked:
            raise SproutError(f"destination is already tracked: {destination}")

        destination_absolute.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source_absolute, destination_absolute)
        try:
            with self.connect() as db:
                db.execute(
                    "UPDATE tracked_paths SET path=? WHERE path=?",
                    (destination_relative, source_relative),
                )
        except Exception:
            if destination_absolute.is_file() and not source_absolute.exists():
                source_absolute.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination_absolute, source_absolute)
            raise
        return source_relative, destination_relative

    def tracked(self) -> set[str]:
        with self.connect() as db:
            return {row[0] for row in db.execute("SELECT path FROM tracked_paths")}

    def tracking_status(self, values: list[Path]) -> list[tuple[str, bool]]:
        """Return tracked state for files, or tracked descendants for directories."""
        tracked = self.tracked()
        results: dict[str, bool] = {}
        for value in values:
            relative = self._relative_file(value, must_exist=False)
            absolute = self.root / Path(relative)
            prefix = relative.rstrip("/") + "/"
            if absolute.is_dir():
                descendants = sorted(path for path in tracked if path.startswith(prefix))
                for path in descendants:
                    results[path] = True
                if not descendants:
                    results[relative + "/"] = False
            else:
                results[relative] = relative in tracked
        return sorted(results.items())

    def untracked_files(self) -> list[str]:
        """List regular project files that are not registered for commits."""
        tracked = self.tracked()
        result: list[str] = []
        for directory, dirs, files in os.walk(self.root, topdown=True, followlinks=False):
            base = Path(directory)
            dirs[:] = [
                name
                for name in dirs
                if name != CONTROL_DIR and not (base / name).is_symlink()
            ]
            for name in files:
                path = base / name
                if path.is_symlink():
                    continue
                normalized = path.relative_to(self.root).as_posix()
                if normalized not in tracked:
                    result.append(normalized)
        return sorted(result)

    @staticmethod
    def hash_file(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        return digest.hexdigest(), size

    def head_branch(self) -> str:
        with self.connect() as db:
            return db.execute("SELECT value FROM meta WHERE key='head_branch'").fetchone()[0]

    def head_commit(self) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT b.commit_id FROM branches b JOIN meta m ON m.value=b.name WHERE m.key='head_branch'"
            ).fetchone()
            return row[0] if row else None

    def manifest(self, commit_id: str | None) -> dict[str, FileState]:
        if commit_id is None:
            return {}
        with self.connect() as db:
            rows = db.execute(
                "SELECT path, object_hash, size, mtime_ns FROM commit_files WHERE commit_id=? ORDER BY path",
                (commit_id,),
            )
            return {
                row["path"]: FileState(row["path"], row["object_hash"], row["size"], row["mtime_ns"])
                for row in rows
            }

    def status(self) -> list[StatusEntry]:
        tracked = self.tracked()
        head = self.manifest(self.head_commit())
        result: list[StatusEntry] = []
        for relative in sorted(tracked | set(head)):
            path = self.root / Path(relative)
            if relative not in tracked or not path.is_file():
                if relative in head:
                    result.append(StatusEntry("deleted", relative))
                continue
            if relative not in head:
                result.append(StatusEntry("added", relative))
                continue
            digest, size = self.hash_file(path)
            if digest != head[relative].object_hash or size != head[relative].size:
                result.append(StatusEntry("modified", relative))
        return result

    def _store_object(self, source: Path) -> tuple[str, int]:
        fd, temp_name = tempfile.mkstemp(dir=self.tmp, prefix="object-")
        digest = hashlib.sha256()
        size = 0
        try:
            with os.fdopen(fd, "wb") as target, source.open("rb") as input_file:
                for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            object_hash = digest.hexdigest()
            destination = self.objects / object_hash[:2] / object_hash
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                existing_hash, existing_size = self.hash_file(destination)
                if existing_hash != object_hash or existing_size != size:
                    raise SproutError(f"corrupt object already exists: {object_hash}")
                Path(temp_name).unlink()
            else:
                os.replace(temp_name, destination)
            return object_hash, size
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise

    @locked
    def commit(self, message: str) -> str:
        if not message.strip():
            raise SproutError("commit message cannot be empty")
        tracked = self.tracked()
        files: list[FileState] = []
        missing: list[str] = []
        for relative in sorted(tracked):
            path = self.root / Path(relative)
            if not path.is_file():
                missing.append(relative)
                continue
            before = path.stat()
            object_hash, size = self._store_object(path)
            after = path.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise SproutError(f"file changed while committing: {relative}")
            files.append(FileState(relative, object_hash, size, after.st_mtime_ns))

        # Modification time is canonical per content object, not versioned metadata.
        # Existing objects keep the time chosen by their first commit. If duplicate
        # content first appears at multiple paths together, use the oldest time.
        hashes = {item.object_hash for item in files}
        existing_times: dict[str, int] = {}
        if hashes:
            placeholders = ",".join("?" for _ in hashes)
            with self.connect() as db:
                rows = db.execute(
                    f"SELECT object_hash, MIN(mtime_ns) FROM commit_files "
                    f"WHERE object_hash IN ({placeholders}) GROUP BY object_hash",
                    tuple(hashes),
                )
                existing_times = {row[0]: row[1] for row in rows}
        first_times: dict[str, int] = {}
        for item in files:
            first_times[item.object_hash] = min(
                first_times.get(item.object_hash, item.mtime_ns), item.mtime_ns
            )
        files = [
            FileState(
                item.path,
                item.object_hash,
                item.size,
                existing_times.get(item.object_hash, first_times[item.object_hash]),
            )
            for item in files
        ]
        parent = self.head_commit()
        previous = self.manifest(parent)
        current = {item.path: item for item in files}
        content_signature = lambda manifest: {
            path: (state.object_hash, state.size) for path, state in manifest.items()
        }
        if parent is not None and content_signature(current) == content_signature(previous):
            raise SproutError("nothing to commit")
        if parent is None and not files:
            raise SproutError("nothing to commit")
        commit_id = uuid.uuid4().hex
        branch = self.head_branch()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                "INSERT INTO commits(id, parent_id, branch_name, created_at, message) VALUES(?,?,?,?,?)",
                (commit_id, parent, branch, created_at, message.strip()),
            )
            db.executemany(
                "INSERT INTO commit_files(commit_id, path, object_hash, size, mtime_ns) VALUES(?,?,?,?,?)",
                ((commit_id, item.path, item.object_hash, item.size, item.mtime_ns) for item in files),
            )
            db.execute("UPDATE branches SET commit_id=? WHERE name=?", (commit_id, branch))
            db.executemany("DELETE FROM tracked_paths WHERE path=?", ((p,) for p in missing))
        return commit_id

    def resolve_commit(self, value: str) -> str:
        if not value.strip():
            raise SproutError("commit id required")
        with self.connect() as db:
            branch = db.execute("SELECT commit_id FROM branches WHERE name=?", (value,)).fetchone()
            if branch is not None:
                if branch[0] is None:
                    raise SproutError(f"branch has no commits: {value}")
                return branch[0]
            rows = db.execute("SELECT id FROM commits WHERE id LIKE ?", (value + "%",)).fetchall()
        if not rows:
            raise SproutError(f"unknown commit: {value}")
        if len(rows) > 1:
            raise SproutError(f"ambiguous commit prefix: {value}")
        return rows[0][0]

    def commit_info(self, value: str) -> tuple[sqlite3.Row, list[FileState]]:
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            row = db.execute("SELECT * FROM commits WHERE id=?", (commit_id,)).fetchone()
        return row, list(self.manifest(commit_id).values())

    def log(self) -> list[sqlite3.Row]:
        current = self.head_commit()
        rows: list[sqlite3.Row] = []
        with self.connect() as db:
            while current:
                row = db.execute("SELECT * FROM commits WHERE id=?", (current,)).fetchone()
                if row is None:
                    raise SproutError(f"broken history at commit: {current}")
                rows.append(row)
                current = row["parent_id"]
        return rows

    def branches(self) -> list[tuple[str, str | None, str]]:
        with self.connect() as db:
            return [
                (row[0], row[1], row[2])
                for row in db.execute("SELECT name, commit_id, comment FROM branches ORDER BY name")
            ]

    @locked
    def create_branch(self, name: str, comment: str = "") -> None:
        if not name or any(c.isspace() for c in name) or name.startswith("-"):
            raise SproutError("branch name must be non-empty and contain no whitespace")
        if HEX_BRANCH_NAME.fullmatch(name):
            raise SproutError("branch name cannot look like a commit id prefix")
        head = self.head_commit()
        if head is None:
            raise SproutError("cannot create branch before first commit")
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO branches(name, commit_id, comment) VALUES(?,?,?)",
                    (name, head, comment.strip()),
                )
        except sqlite3.IntegrityError as exc:
            raise SproutError(f"branch already exists: {name}") from exc

    @locked
    def set_branch_comment(self, name: str, comment: str) -> None:
        with self.connect() as db:
            cursor = db.execute("UPDATE branches SET comment=? WHERE name=?", (comment.strip(), name))
            if cursor.rowcount == 0:
                raise SproutError(f"unknown branch: {name}")

    def _verify_manifest(self, target: dict[str, FileState]) -> None:
        for item in target.values():
            source = self.objects / item.object_hash[:2] / item.object_hash
            if not source.is_file():
                raise SproutError(f"missing object {item.object_hash} for {item.path}")
            digest, size = self.hash_file(source)
            if digest != item.object_hash or size != item.size:
                raise SproutError(f"corrupt object {item.object_hash} for {item.path}")

    def _set_active_operation(self, operation_id: str) -> None:
        with self.connect() as db:
            db.execute("UPDATE meta SET value=? WHERE key='active_operation'", (operation_id,))

    def _rollback_materialization(self, operation_dir: Path, plan: dict[str, Any]) -> None:
        staged = operation_dir / "staged"
        backup = operation_dir / "backup"
        # A new target whose staged copy disappeared was installed and must be removed.
        for relative in plan["new_paths"]:
            if not (staged / Path(relative)).exists():
                destination = self.root / Path(relative)
                if destination.is_file():
                    destination.unlink()
        # Backup presence is the durable record that an original file was moved.
        if backup.exists():
            for saved in sorted((path for path in backup.rglob("*") if path.is_file()), reverse=True):
                relative = saved.relative_to(backup)
                destination = self.root / relative
                if destination.is_file():
                    destination.unlink()
                elif destination.exists():
                    raise SproutError(f"cannot roll back non-file path: {relative.as_posix()}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(saved, destination)

    def _recover_pending_materialization(self) -> None:
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()
        if row is None:
            raise SproutError("repository is missing operation metadata")
        active = row[0]
        operation_dirs = [path for path in self.tmp.glob("restore-*") if path.is_dir()]
        if active:
            operation_dir = self.tmp / active
            plan_path = operation_dir / "plan.json"
            if not plan_path.is_file():
                raise SproutError(f"cannot recover interrupted operation: {active}")
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                self._rollback_materialization(operation_dir, plan)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise SproutError(f"cannot recover interrupted operation: {active}") from exc
            self._set_active_operation("")
        for operation_dir in operation_dirs:
            shutil.rmtree(operation_dir, ignore_errors=True)

    def _write_operation_plan(self, path: Path, plan: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(plan, file, ensure_ascii=False, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())

    def _finalize_materialization(
        self, target: dict[str, FileState], head_branch: str | None
    ) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM tracked_paths")
            db.executemany("INSERT INTO tracked_paths(path) VALUES(?)", ((p,) for p in target))
            if head_branch is not None:
                db.execute("UPDATE meta SET value=? WHERE key='head_branch'", (head_branch,))
            db.execute("UPDATE meta SET value='' WHERE key='active_operation'")

    def _materialize(self, target: dict[str, FileState], *, head_branch: str | None = None) -> None:
        current = self.tracked()
        self._verify_manifest(target)
        for relative in set(target) - current:
            destination = self.root / Path(relative)
            if destination.exists():
                raise SproutError(f"untracked path would be overwritten: {relative}")

        operation_id = "restore-" + uuid.uuid4().hex
        operation_dir = self.tmp / operation_id
        operation_dir.mkdir()
        staged = operation_dir / "staged"
        backup = operation_dir / "backup"
        changed = current | set(target)
        plan = {"new_paths": sorted(set(target) - current)}
        active_registered = False
        operation_complete = False
        try:
            for relative, item in target.items():
                output = staged / Path(relative)
                output.parent.mkdir(parents=True, exist_ok=True)
                source = self.objects / item.object_hash[:2] / item.object_hash
                shutil.copyfile(source, output)
            self._write_operation_plan(operation_dir / "plan.json", plan)
            self._set_active_operation(operation_id)
            active_registered = True
            for relative in sorted(changed):
                destination = self.root / Path(relative)
                if destination.is_file():
                    saved = backup / Path(relative)
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(destination, saved)
                elif destination.exists():
                    raise SproutError(f"cannot replace non-file path: {relative}")
            for relative in sorted(target):
                source = staged / Path(relative)
                destination = self.root / Path(relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, destination)
                # Record installation before metadata work so rollback includes it.
                os.utime(destination, ns=(target[relative].mtime_ns, target[relative].mtime_ns))
            self._finalize_materialization(target, head_branch)
            operation_complete = True
        except Exception:
            try:
                self._rollback_materialization(operation_dir, plan)
                if active_registered:
                    self._set_active_operation("")
                    active_registered = False
            except Exception as rollback_exc:
                raise SproutError(
                    "restore failed and automatic rollback was incomplete; rerun Sprout to recover"
                ) from rollback_exc
            raise
        finally:
            if operation_complete or not active_registered:
                shutil.rmtree(operation_dir, ignore_errors=True)

    def _is_saved_file_state(self, relative: str, object_hash: str, size: int) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 FROM commit_files WHERE path=? AND object_hash=? AND size=? LIMIT 1",
                (relative, object_hash, size),
            ).fetchone()
        return row is not None

    def _working_content_signature(self) -> dict[str, tuple[str, int]] | None:
        signature: dict[str, tuple[str, int]] = {}
        for relative in sorted(self.tracked()):
            path = self.root / Path(relative)
            if not path.is_file():
                return None
            object_hash, size = self.hash_file(path)
            signature[relative] = (object_hash, size)
        return signature

    def _is_saved_snapshot(self, signature: dict[str, tuple[str, int]]) -> bool:
        commits: dict[str, dict[str, tuple[str, int]]] = {}
        with self.connect() as db:
            commit_ids = [row[0] for row in db.execute("SELECT id FROM commits")]
            rows = db.execute(
                "SELECT commit_id, path, object_hash, size FROM commit_files ORDER BY commit_id, path"
            )
            for row in rows:
                commits.setdefault(row["commit_id"], {})[row["path"]] = (
                    row["object_hash"],
                    row["size"],
                )
        for commit_id in commit_ids:
            if commits.get(commit_id, {}) == signature:
                return True
        return False

    def _has_unsaved_changes(self) -> bool:
        if not self.status():
            return False
        signature = self._working_content_signature()
        if signature is None:
            return True
        return not self._is_saved_snapshot(signature)

    def _refuse_losing_added_files(self, target: dict[str, FileState]) -> None:
        current = self.tracked()
        head = self.manifest(self.head_commit())
        unsafe = []
        for relative in sorted(current - set(head)):
            path = self.root / Path(relative)
            if not path.is_file():
                continue
            object_hash, size = self.hash_file(path)
            if relative in target and (target[relative].object_hash, target[relative].size) == (
                object_hash,
                size,
            ):
                continue
            if self._is_saved_file_state(relative, object_hash, size):
                continue
            unsafe.append(relative)
        if unsafe:
            paths = ", ".join(unsafe[:3])
            if len(unsafe) > 3:
                paths += f", ... ({len(unsafe)} files)"
            raise SproutError(
                "discard would delete tracked files that have never been committed; "
                f"commit or untrack them first: {paths}"
            )

    @locked
    def restore(self, value: str, *, discard: bool = False) -> str:
        if self._has_unsaved_changes() and not discard:
            raise SproutError("working tree has uncommitted changes (use --discard to replace them)")
        commit_id = self.resolve_commit(value)
        target = self.manifest(commit_id)
        if discard:
            self._refuse_losing_added_files(target)
        self._materialize(target)
        return commit_id

    @locked
    def switch(self, name: str, *, discard: bool = False) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT commit_id FROM branches WHERE name=?", (name,)).fetchone()
        if row is None:
            raise SproutError(f"unknown branch: {name}")
        if self._has_unsaved_changes() and not discard:
            raise SproutError("working tree has uncommitted changes (use --discard to replace them)")
        target = self.manifest(row[0])
        if discard:
            self._refuse_losing_added_files(target)
        self._materialize(target, head_branch=name)
        return row[0]
