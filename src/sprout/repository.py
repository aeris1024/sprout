from __future__ import annotations

import fnmatch
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
IGNORE_FILE = ".sproutignore"
SCHEMA_VERSION = "1"
HEX_BRANCH_NAME = re.compile(r"^[0-9a-f]{4,}$")
HEX_COMMIT_REFERENCE = re.compile(r"^[0-9a-f]+$")
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


@dataclass(frozen=True)
class DiffEntry:
    state: str
    path: str
    old_size: int | None = None
    new_size: int | None = None


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    directory_only: bool


@dataclass(frozen=True)
class GcResult:
    dry_run: bool
    removed_objects: int
    removed_temps: int
    freed_bytes: int
    objects: tuple[str, ...]
    temps: tuple[str, ...]


@dataclass(frozen=True)
class DoctorIssue:
    kind: str
    detail: str


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    checked_objects: int
    issues: tuple[DoctorIssue, ...]


@dataclass(frozen=True)
class RepoStats:
    commits: int
    branches: int
    tracked_paths: int
    objects: int
    objects_bytes: int
    logical_bytes: int
    unique_bytes: int

    @property
    def dedup_saved_bytes(self) -> int:
        return max(0, self.logical_bytes - self.unique_bytes)


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
                # Peek without the repository lock so read-only commands can run
                # while a long write holds it. Recover only when an interrupted
                # operation is recorded; re-check under the lock inside recover.
                with repo.connect() as db:
                    row = db.execute(
                        "SELECT value FROM meta WHERE key='active_operation'"
                    ).fetchone()
                if row is None:
                    raise SproutError("repository is missing operation metadata")
                if row[0]:
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

    @staticmethod
    def _path_key(path: str) -> str:
        return os.path.normcase(path) if os.name == "nt" else path

    def _ignore_rules(self) -> list[IgnoreRule]:
        path = self.root / IGNORE_FILE
        if not path.is_file():
            return []
        rules: list[IgnoreRule] = []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            directory_only = line.endswith("/")
            pattern = line[:-1] if directory_only else line
            if pattern:
                rules.append(IgnoreRule(pattern.replace("\\", "/"), directory_only))
        return rules

    @staticmethod
    def _is_ignored(relative: str, rules: list[IgnoreRule], *, is_dir: bool = False) -> bool:
        if not rules:
            return False
        relative = relative.replace("\\", "/").strip("/")
        if not relative:
            return False
        name = relative.rsplit("/", 1)[-1]
        for rule in rules:
            if rule.directory_only:
                if relative == rule.pattern or relative.startswith(rule.pattern + "/"):
                    return True
                parts = relative.split("/")
                limit = len(parts) if is_dir else len(parts) - 1
                for index in range(limit):
                    ancestor = "/".join(parts[: index + 1])
                    ancestor_name = parts[index]
                    if fnmatch.fnmatch(ancestor, rule.pattern) or fnmatch.fnmatch(
                        ancestor_name, rule.pattern
                    ):
                        return True
            elif fnmatch.fnmatch(relative, rule.pattern) or fnmatch.fnmatch(name, rule.pattern):
                return True
        return False

    @locked
    def track(self, values: list[Path]) -> list[str]:
        paths: set[str] = set()
        rules = self._ignore_rules()
        for value in values:
            absolute = (value if value.is_absolute() else Path.cwd() / value)
            if absolute.is_symlink():
                raise SproutError(f"symbolic links are not supported: {value}")
            if absolute.is_dir():
                self._relative_file(absolute)
                for directory, dirs, files in os.walk(absolute, topdown=True, followlinks=False):
                    base = Path(directory)
                    kept_dirs: list[str] = []
                    for name in dirs:
                        child = base / name
                        if child.is_symlink():
                            continue
                        relative_dir = child.relative_to(self.root).as_posix()
                        if CONTROL_DIR in Path(relative_dir).parts:
                            continue
                        if self._is_ignored(relative_dir, rules, is_dir=True):
                            continue
                        kept_dirs.append(name)
                    dirs[:] = kept_dirs
                    for name in files:
                        child = base / name
                        if child.is_symlink():
                            continue
                        relative = self._relative_file(child)
                        if CONTROL_DIR in Path(relative).parts:
                            continue
                        if self._is_ignored(relative, rules):
                            continue
                        paths.add(relative)
            elif absolute.is_file():
                # Explicit file paths bypass ignore rules, like git add --force for a path.
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
                relative_key = self._path_key(relative)
                prefix_key = relative_key.rstrip("/\\") + os.sep
                requested.extend(
                    path
                    for path in tracked
                    if self._path_key(path) == relative_key
                    or self._path_key(path).startswith(prefix_key)
                )
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
        rules = self._ignore_rules()
        result: list[str] = []
        for directory, dirs, files in os.walk(self.root, topdown=True, followlinks=False):
            base = Path(directory)
            kept_dirs: list[str] = []
            for name in dirs:
                if name == CONTROL_DIR:
                    continue
                child = base / name
                if child.is_symlink():
                    continue
                relative_dir = child.relative_to(self.root).as_posix()
                if self._is_ignored(relative_dir, rules, is_dir=True):
                    continue
                kept_dirs.append(name)
            dirs[:] = kept_dirs
            for name in files:
                path = base / name
                if path.is_symlink():
                    continue
                normalized = path.relative_to(self.root).as_posix()
                if normalized in tracked:
                    continue
                if self._is_ignored(normalized, rules):
                    continue
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

    @staticmethod
    def diff_manifests(
        before: dict[str, FileState], after: dict[str, FileState]
    ) -> list[DiffEntry]:
        result: list[DiffEntry] = []
        for relative in sorted(set(before) | set(after)):
            if relative not in before:
                item = after[relative]
                result.append(DiffEntry("added", relative, None, item.size))
            elif relative not in after:
                item = before[relative]
                result.append(DiffEntry("deleted", relative, item.size, None))
            else:
                left = before[relative]
                right = after[relative]
                if left.object_hash != right.object_hash or left.size != right.size:
                    result.append(DiffEntry("modified", relative, left.size, right.size))
        return result

    def _working_tree_manifest(self) -> dict[str, FileState]:
        result: dict[str, FileState] = {}
        for relative in self.tracked():
            path = self.root / Path(relative)
            if not path.is_file():
                continue
            digest, size = self.hash_file(path)
            result[relative] = FileState(relative, digest, size, 0)
        return result

    def diff(
        self, commit_a: str | None = None, commit_b: str | None = None
    ) -> list[DiffEntry]:
        if commit_a is None and commit_b is None:
            before = self.manifest(self.head_commit())
            after = self._working_tree_manifest()
        elif commit_b is None:
            before = self.manifest(self.resolve_commit(commit_a))
            after = self._working_tree_manifest()
        else:
            before = self.manifest(self.resolve_commit(commit_a))
            after = self.manifest(self.resolve_commit(commit_b))
        return self.diff_manifests(before, after)

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
            if HEX_COMMIT_REFERENCE.fullmatch(value) is None:
                raise SproutError(f"unknown commit: {value}")
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

    @staticmethod
    def _commit_path_hash(db: sqlite3.Connection, commit_id: str, path: str) -> str | None:
        row = db.execute(
            "SELECT object_hash FROM commit_files WHERE commit_id=? AND path=?",
            (commit_id, path),
        ).fetchone()
        return row[0] if row else None

    def log(self, path: Path | None = None) -> list[sqlite3.Row]:
        relative: str | None = None
        if path is not None:
            relative = self._relative_file(path, must_exist=False)
        current = self.head_commit()
        rows: list[sqlite3.Row] = []
        with self.connect() as db:
            while current:
                row = db.execute("SELECT * FROM commits WHERE id=?", (current,)).fetchone()
                if row is None:
                    raise SproutError(f"broken history at commit: {current}")
                if relative is None:
                    rows.append(row)
                else:
                    current_hash = self._commit_path_hash(db, current, relative)
                    parent_id = row["parent_id"]
                    parent_hash = (
                        self._commit_path_hash(db, parent_id, relative) if parent_id else None
                    )
                    if current_hash != parent_hash:
                        rows.append(row)
                current = row["parent_id"]
        return rows

    def referenced_object_hashes(self) -> set[str]:
        """Return object hashes still referenced by any commit."""
        with self.connect() as db:
            return {row[0] for row in db.execute("SELECT DISTINCT object_hash FROM commit_files")}

    def doctor(self) -> DoctorResult:
        """Inspect repository integrity without changing the working tree."""
        issues: list[DoctorIssue] = []
        with self.connect() as db:
            hashes = [
                row[0]
                for row in db.execute("SELECT DISTINCT object_hash FROM commit_files ORDER BY 1")
            ]
            active = db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()
            if active is not None and active[0]:
                issues.append(
                    DoctorIssue("active_operation", f"interrupted operation recorded: {active[0]}")
                )

        for object_hash in hashes:
            path = self.objects / object_hash[:2] / object_hash
            if not path.is_file():
                issues.append(DoctorIssue("missing_object", object_hash))
                continue
            digest, _ = self.hash_file(path)
            if digest != object_hash:
                issues.append(DoctorIssue("corrupt_object", object_hash))

        if self.tmp.is_dir():
            for path in sorted(path for path in self.tmp.glob("object-*") if path.is_file()):
                issues.append(DoctorIssue("orphan_temp", path.name))

        return DoctorResult(
            ok=not issues,
            checked_objects=len(hashes),
            issues=tuple(issues),
        )

    def stats(self) -> RepoStats:
        """Summarize repository size and basic counts without changing files."""
        with self.connect() as db:
            commits = db.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
            branches = db.execute("SELECT COUNT(*) FROM branches").fetchone()[0]
            tracked_paths = db.execute("SELECT COUNT(*) FROM tracked_paths").fetchone()[0]
            logical_bytes = db.execute(
                "SELECT COALESCE(SUM(size), 0) FROM commit_files"
            ).fetchone()[0]
            unique_bytes = db.execute(
                "SELECT COALESCE(SUM(size), 0) FROM ("
                "SELECT object_hash, MAX(size) AS size FROM commit_files GROUP BY object_hash"
                ")"
            ).fetchone()[0]

        objects = 0
        objects_bytes = 0
        if self.objects.is_dir():
            for shard in self.objects.iterdir():
                if not shard.is_dir():
                    continue
                for path in shard.iterdir():
                    if path.is_file():
                        objects += 1
                        objects_bytes += path.stat().st_size

        return RepoStats(
            commits=commits,
            branches=branches,
            tracked_paths=tracked_paths,
            objects=objects,
            objects_bytes=objects_bytes,
            logical_bytes=logical_bytes,
            unique_bytes=unique_bytes,
        )

    @locked
    def gc(self, *, dry_run: bool = False) -> GcResult:
        """Delete unreferenced objects and leftover object temp files."""
        referenced = self.referenced_object_hashes()
        object_targets: list[tuple[Path, int]] = []
        if self.objects.is_dir():
            for shard in sorted(path for path in self.objects.iterdir() if path.is_dir()):
                for path in sorted(path for path in shard.iterdir() if path.is_file()):
                    if path.name not in referenced:
                        object_targets.append((path, path.stat().st_size))

        temp_targets: list[tuple[Path, int]] = []
        if self.tmp.is_dir():
            for path in sorted(path for path in self.tmp.glob("object-*") if path.is_file()):
                temp_targets.append((path, path.stat().st_size))

        freed_bytes = sum(size for _, size in object_targets) + sum(size for _, size in temp_targets)
        if not dry_run:
            for path, _ in object_targets:
                path.unlink()
            if self.objects.is_dir():
                for shard in sorted(
                    (path for path in self.objects.iterdir() if path.is_dir()),
                    key=lambda path: path.name,
                ):
                    try:
                        shard.rmdir()
                    except OSError:
                        pass
            for path, _ in temp_targets:
                path.unlink(missing_ok=True)

        return GcResult(
            dry_run=dry_run,
            removed_objects=len(object_targets),
            removed_temps=len(temp_targets),
            freed_bytes=freed_bytes,
            objects=tuple(path.name for path, _ in object_targets),
            temps=tuple(path.name for path, _ in temp_targets),
        )

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
        self, target: dict[str, FileState], head_branch: str | None, *, partial: bool = False
    ) -> None:
        with self.connect() as db:
            if partial:
                db.executemany(
                    "INSERT OR IGNORE INTO tracked_paths(path) VALUES(?)",
                    ((path,) for path in target),
                )
            else:
                db.execute("DELETE FROM tracked_paths")
                db.executemany(
                    "INSERT INTO tracked_paths(path) VALUES(?)", ((path,) for path in target)
                )
            if head_branch is not None:
                db.execute("UPDATE meta SET value=? WHERE key='head_branch'", (head_branch,))
            db.execute("UPDATE meta SET value='' WHERE key='active_operation'")

    def _remove_empty_parents(self, paths: set[str]) -> None:
        candidates: set[Path] = set()
        for relative in paths:
            directory = (self.root / Path(relative)).parent
            while directory != self.root:
                if directory != self.control:
                    candidates.add(directory)
                directory = directory.parent
        for directory in sorted(candidates, key=lambda path: len(path.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass

    def _materialize(
        self,
        target: dict[str, FileState],
        *,
        head_branch: str | None = None,
        partial: bool = False,
    ) -> None:
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
        changed = set(target) if partial else current | set(target)
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
            self._finalize_materialization(target, head_branch, partial=partial)
            if not partial:
                self._remove_empty_parents(current - set(target))
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

    def _working_content_signature(self) -> dict[str, tuple[str, int]] | None:
        signature: dict[str, tuple[str, int]] = {}
        for relative in sorted(self.tracked()):
            path = self.root / Path(relative)
            if not path.is_file():
                return None
            object_hash, size = self.hash_file(path)
            signature[relative] = (object_hash, size)
        return signature

    def _is_saved_snapshot(
        self, signature: dict[str, tuple[str, int]], *, exact: bool = True
    ) -> bool:
        if not exact:
            if not signature:
                return True
            with self.connect() as db:
                matching: set[str] | None = None
                for path, (object_hash, size) in signature.items():
                    rows = {
                        row[0]
                        for row in db.execute(
                            "SELECT commit_id FROM commit_files "
                            "WHERE path=? AND object_hash=? AND size=?",
                            (path, object_hash, size),
                        )
                    }
                    matching = rows if matching is None else matching & rows
                    if not matching:
                        return False
                return True

        file_count = len(signature)
        with self.connect() as db:
            if file_count == 0:
                row = db.execute(
                    """
                    SELECT c.id
                    FROM commits c
                    LEFT JOIN commit_files f ON f.commit_id = c.id
                    GROUP BY c.id
                    HAVING COUNT(f.path) = 0
                    LIMIT 1
                    """
                ).fetchone()
                return row is not None

            candidates = [
                row[0]
                for row in db.execute(
                    """
                    SELECT commit_id
                    FROM commit_files
                    GROUP BY commit_id
                    HAVING COUNT(*) = ?
                    """,
                    (file_count,),
                )
            ]
            for commit_id in candidates:
                rows = db.execute(
                    "SELECT path, object_hash, size FROM commit_files WHERE commit_id=?",
                    (commit_id,),
                )
                manifest = {
                    row["path"]: (row["object_hash"], row["size"]) for row in rows
                }
                if manifest == signature:
                    return True
        return False

    def _has_unsaved_changes(self, paths: set[str] | None = None) -> bool:
        tracked = self.tracked()
        head = self.manifest(self.head_commit())
        if paths is None:
            hash_paths = tracked
            status_paths = tracked | set(head)
            exact = True
        else:
            hash_paths = tracked & paths
            status_paths = paths
            exact = False

        signature: dict[str, tuple[str, int]] | None = {}
        for relative in sorted(hash_paths):
            path = self.root / Path(relative)
            if not path.is_file():
                signature = None
                break
            signature[relative] = self.hash_file(path)

        has_changes = False
        for relative in sorted(status_paths):
            path = self.root / Path(relative)
            if relative not in tracked or not path.is_file():
                if relative in head:
                    has_changes = True
                continue
            if signature is None:
                has_changes = True
                continue
            if relative not in head:
                has_changes = True
                continue
            digest, size = signature[relative]
            if digest != head[relative].object_hash or size != head[relative].size:
                has_changes = True

        if not has_changes:
            return False
        if signature is None:
            return True
        return not self._is_saved_snapshot(signature, exact=exact)

    def _resolve_restore_paths(
        self, values: list[Path], manifest: dict[str, FileState]
    ) -> set[str]:
        selected: set[str] = set()
        for value in values:
            relative = self._relative_file(value, must_exist=False)
            if relative in manifest:
                selected.add(relative)
                continue
            prefix = relative.rstrip("/") + "/"
            matches = {path for path in manifest if path.startswith(prefix)}
            if not matches:
                raise SproutError(f"path not in commit: {relative}")
            selected.update(matches)
        return selected

    @locked
    def restore(
        self,
        value: str,
        paths: list[Path] | None = None,
        *,
        discard: bool = False,
    ) -> str:
        commit_id = self.resolve_commit(value)
        commit_manifest = self.manifest(commit_id)
        if paths:
            selected = self._resolve_restore_paths(paths, commit_manifest)
            if self._has_unsaved_changes(selected) and not discard:
                raise SproutError(
                    "working tree has uncommitted changes (use --discard to replace them)"
                )
            target = {path: commit_manifest[path] for path in selected}
            self._materialize(target, partial=True)
        else:
            if self._has_unsaved_changes() and not discard:
                raise SproutError(
                    "working tree has uncommitted changes (use --discard to replace them)"
                )
            self._materialize(commit_manifest)
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
        self._materialize(target, head_branch=name)
        return row[0]
