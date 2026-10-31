from __future__ import annotations

import fnmatch
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import time
import unicodedata
import uuid
import warnings
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable, Iterator, TypeVar

import zstandard
from PIL import Image, ImageOps, UnidentifiedImageError

from . import __version__
from . import trash as recovery
from . import archive as static_archive
from .cache import WorktreeCache
from .errors import SproutError

CONTROL_DIR = ".sprout"
DB_NAME = "repository.db"
IGNORE_FILE = ".sproutignore"
SCHEMA_VERSION = "1"
RESTORE_PLAN_VERSION = 1
OBJECT_COMPRESSION = "zstd"
OBJECT_COMPRESSION_LEVEL = 3
IO_CHUNK_SIZE = 1024 * 1024
# Coarsest common modification-time granularity (FAT keeps 2 seconds).
RACY_MARGIN_NS = 2_000_000_000
THUMBNAIL_ROLE = "thumbnail"
PREVIEW_ROLE = "preview"
# Previews have no fixed size limit; larger files need explicit confirmation.
PREVIEW_CONFIRM_BYTES = 100 * 1024 * 1024
PREVIEW_DEFAULT_MEDIA_TYPE = "application/octet-stream"
MEDIA_TYPE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$"
)
THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
THUMBNAIL_MAX_DIMENSION = 4096
NOTE_MAX_CHARS = 20_000
LABEL_MAX_CHARS = 64
LABEL_MAX_COUNT = 32
COVER_META_KEY = "cover_file_id"
COVER_SIDE = 512
COVER_MAX_BYTES = 200 * 1024 * 1024
COVER_MAX_PIXELS = 64_000_000
COVER_FORMATS = {"PNG", "JPEG", "WEBP", "BMP"}
THUMBNAIL_MEDIA_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
HEX_BRANCH_NAME = re.compile(r"^[0-9a-f]{4,}$")
HEX_COMMIT_REFERENCE = re.compile(r"^[0-9a-f]+$")
T = TypeVar("T")
ProgressCallback = Callable[[str, int, int], None]
UNCHANGED = object()

SEQUENCE_TABLES = ("commits", "buds", "trash_entries")
REQUIRED_SCHEMA_TABLES = {
    "id_sequences",
    "preview_assets",
    "file_identities",
    "meta",
    "trash_entries",
    "trash_objects",
    "objects",
    "commits",
    "commit_files",
    "commit_attachments",
    "commit_notes",
    "commit_labels",
    "branches",
    "tags",
    "tracked_paths",
    "repository_state",
    "buds",
    "bud_files",
}
REQUIRED_META_KEYS = {
    "schema_version",
    "object_compression",
    "active_operation",
    "repository_id",
    "repository_created_at",
}


def locked(method: Callable[..., T]) -> Callable[..., T]:
    """Serialize repository mutations across processes."""

    @wraps(method)
    def wrapper(self: Repository, *args: Any, **kwargs: Any) -> T:
        with self.lock():
            return method(self, *args, **kwargs)

    return wrapper


TIMESTAMP_GLOB = (
    "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]"
    ".[0-9][0-9][0-9][0-9][0-9][0-9]+00:00"
)
TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00")
OBJECT_HASH_CHECK = "length({0}) = 64 AND {0} NOT GLOB '*[^0-9a-f]*'"
# Candidate commits containing one exact file; indexed by idx_commit_files_object.
SAVED_FILE_COMMITS_SQL = (
    "SELECT commit_id FROM commit_files WHERE object_hash=? AND size=? AND path=?"
)


def utc_timestamp(moment: datetime | None = None) -> str:
    """Format every stored time identically: UTC with microsecond precision."""
    moment = datetime.now(timezone.utc) if moment is None else moment.astimezone(timezone.utc)
    return moment.isoformat(timespec="microseconds")


def path_key(path: str) -> str:
    """Identify a path across letter case and Unicode composition on every OS."""
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", path).casefold())


def reject_path_conflicts(paths: Iterable[str]) -> None:
    """Reject paths that would land on one file, or on a file and its descendant."""
    by_key: dict[str, str] = {}
    for path in sorted(paths):
        other = by_key.setdefault(path_key(path), path)
        if other != path:
            raise SproutError(
                f"path conflicts with {other}: {path}",
                code="path_case_conflict",
                details={"path": path, "conflicting_path": other},
            )
    for key, path in by_key.items():
        parts = key.split("/")
        for index in range(1, len(parts)):
            other = by_key.get("/".join(parts[:index]))
            if other is not None:
                raise SproutError(
                    f"path conflicts with {other}: {path}",
                    code="path_case_conflict",
                    details={"path": path, "conflicting_path": other},
                )


SCHEMA = f"""
PRAGMA foreign_keys = ON;
CREATE TABLE meta (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);
CREATE TABLE id_sequences (
    name TEXT PRIMARY KEY NOT NULL CHECK (name IN ('commits', 'buds', 'trash_entries')),
    last_value INTEGER NOT NULL DEFAULT 0 CHECK (typeof(last_value) = 'integer' AND last_value >= 0)
);
CREATE TABLE objects (
    hash TEXT PRIMARY KEY NOT NULL CHECK ({OBJECT_HASH_CHECK.format("hash")}),
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    stored_size INTEGER NOT NULL CHECK (typeof(stored_size) = 'integer' AND stored_size >= 0),
    encoding TEXT NOT NULL CHECK (encoding <> ''),
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}'),
    UNIQUE (hash, size)
);
CREATE TABLE trash_entries (
    id TEXT PRIMARY KEY NOT NULL,
    seq INTEGER NOT NULL UNIQUE CHECK (typeof(seq) = 'integer' AND seq > 0),
    kind TEXT NOT NULL CHECK (kind IN ('commit', 'preview_delete', 'preview_replace', 'bud_delete', 'discard', 'note_delete', 'tag_delete', 'branch_delete')),
    target_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}'),
    payload TEXT NOT NULL
);
CREATE TABLE trash_objects (
    trash_id TEXT NOT NULL REFERENCES trash_entries(id) ON DELETE CASCADE,
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    PRIMARY KEY (trash_id, object_hash),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE INDEX idx_trash_objects_object ON trash_objects(object_hash, size);
CREATE TABLE branches (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    commit_id TEXT REFERENCES commits(id),
    comment TEXT NOT NULL DEFAULT '',
    deleted INTEGER NOT NULL DEFAULT 0 CHECK (deleted IN (0, 1)),
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}'),
    deleted_at TEXT CHECK (deleted_at IS NULL OR deleted_at GLOB '{TIMESTAMP_GLOB}'),
    CHECK (deleted = 0 OR commit_id IS NULL),
    CHECK ((deleted = 0) = (deleted_at IS NULL))
);
CREATE UNIQUE INDEX idx_branches_live_name ON branches(name) WHERE deleted = 0;
CREATE TABLE commits (
    id TEXT PRIMARY KEY NOT NULL,
    seq INTEGER NOT NULL UNIQUE CHECK (typeof(seq) = 'integer' AND seq > 0),
    parent_id TEXT REFERENCES commits(id),
    branch_id TEXT NOT NULL REFERENCES branches(id),
    branch_name TEXT NOT NULL,
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}'),
    message TEXT NOT NULL
);
CREATE TABLE repository_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    head_branch_id TEXT NOT NULL REFERENCES branches(id),
    current_commit_id TEXT REFERENCES commits(id)
);
CREATE TABLE file_identities (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id)=32 AND id NOT GLOB '*[^0-9a-f]*')
);
CREATE TABLE commit_files (
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    path_key TEXT NOT NULL,
    file_id TEXT NOT NULL REFERENCES file_identities(id),
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    mtime_ns INTEGER NOT NULL CHECK (typeof(mtime_ns) = 'integer'),
    PRIMARY KEY (commit_id, path),
    UNIQUE (commit_id, path_key),
    UNIQUE (commit_id, file_id),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE TABLE commit_attachments (
    id TEXT PRIMARY KEY NOT NULL,
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0 CHECK (typeof(position) = 'integer' AND position >= 0),
    original_name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '' CHECK (length(display_name)<=256 AND instr(display_name,char(10))=0 AND instr(display_name,char(13))=0),
    description TEXT NOT NULL DEFAULT '' CHECK (length(description)<=20000),
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
    media_type TEXT NOT NULL,
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}'),
    updated_at TEXT NOT NULL CHECK (updated_at GLOB '{TIMESTAMP_GLOB}'),
    CHECK (role='preview' OR (display_name='' AND description='' AND is_primary=0)),
    UNIQUE (id, commit_id, role),
    UNIQUE (commit_id, role, position),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE UNIQUE INDEX idx_single_thumbnail ON commit_attachments(commit_id)
    WHERE role = 'thumbnail';
CREATE UNIQUE INDEX idx_primary_preview ON commit_attachments(commit_id) WHERE role='preview' AND is_primary=1;
CREATE TABLE preview_assets (
    attachment_id TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'preview' CHECK (role='preview'),
    PRIMARY KEY (attachment_id,file_id),
    FOREIGN KEY (attachment_id,commit_id,role) REFERENCES commit_attachments(id,commit_id,role) ON DELETE CASCADE,
    FOREIGN KEY (commit_id,file_id) REFERENCES commit_files(commit_id,file_id) ON DELETE CASCADE
);
CREATE INDEX idx_preview_assets_attachment ON preview_assets(attachment_id,commit_id,role);
CREATE INDEX idx_preview_assets_file ON preview_assets(commit_id,file_id);
CREATE TABLE commit_notes (
    commit_id TEXT PRIMARY KEY NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    updated_at TEXT NOT NULL CHECK (updated_at GLOB '{TIMESTAMP_GLOB}')
);
CREATE TABLE commit_labels (
    commit_id TEXT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    PRIMARY KEY (commit_id, label)
);
CREATE TABLE tags (
    name TEXT PRIMARY KEY NOT NULL,
    commit_id TEXT NOT NULL REFERENCES commits(id),
    comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}')
);
CREATE TABLE tracked_paths (
    path TEXT PRIMARY KEY NOT NULL,
    path_key TEXT NOT NULL UNIQUE,
    file_id TEXT NOT NULL UNIQUE REFERENCES file_identities(id)
);
CREATE TABLE buds (
    id TEXT PRIMARY KEY NOT NULL,
    seq INTEGER NOT NULL UNIQUE CHECK (typeof(seq) = 'integer' AND seq > 0),
    base_commit_id TEXT REFERENCES commits(id),
    branch_id TEXT NOT NULL REFERENCES branches(id),
    branch_name TEXT NOT NULL,
    created_at TEXT NOT NULL CHECK (created_at GLOB '{TIMESTAMP_GLOB}'),
    name TEXT NOT NULL DEFAULT '' CHECK (length(name) <= 256 AND instr(name, char(10)) = 0 AND instr(name, char(13)) = 0)
);
CREATE TABLE bud_files (
    bud_id TEXT NOT NULL REFERENCES buds(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    path_key TEXT NOT NULL,
    file_id TEXT NOT NULL REFERENCES file_identities(id),
    object_hash TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size) = 'integer' AND size >= 0),
    mtime_ns INTEGER NOT NULL CHECK (typeof(mtime_ns) = 'integer'),
    PRIMARY KEY (bud_id, path),
    UNIQUE (bud_id, path_key),
    UNIQUE (bud_id, file_id),
    FOREIGN KEY (object_hash, size) REFERENCES objects(hash, size)
);
CREATE INDEX idx_commit_files_identity ON commit_files(file_id);
CREATE INDEX idx_bud_files_identity ON bud_files(file_id);
CREATE INDEX idx_commits_parent ON commits(parent_id);
CREATE INDEX idx_commits_branch ON commits(branch_id);
CREATE INDEX idx_branches_commit ON branches(commit_id);
CREATE INDEX idx_tags_commit ON tags(commit_id);
CREATE INDEX idx_commit_files_object ON commit_files(object_hash, size);
CREATE INDEX idx_commit_attachments_object ON commit_attachments(object_hash, size);
CREATE INDEX idx_commit_labels_label ON commit_labels(label);
CREATE INDEX idx_buds_base ON buds(base_commit_id);
CREATE INDEX idx_buds_branch ON buds(branch_id);
CREATE INDEX idx_bud_files_object ON bud_files(object_hash, size);
"""


@lru_cache(maxsize=1)
def expected_schema() -> dict[str, str]:
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(SCHEMA)
        return {
            row[0]: row[1]
            for row in db.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL")
        }


@dataclass(frozen=True)
class FileState:
    path: str
    object_hash: str
    size: int
    mtime_ns: int
    file_id: str = ""


@dataclass(frozen=True)
class StatusEntry:
    state: str
    path: str
    previous_path: str | None = None


@dataclass(frozen=True)
class DiffEntry:
    state: str
    path: str
    old_size: int | None = None
    new_size: int | None = None
    previous_path: str | None = None


@dataclass(frozen=True)
class CoverOutcome:
    """Whether a save could use the cover file, and why not when it could not."""

    applied: bool
    reason: str | None = None


@dataclass(frozen=True)
class CommitResult:
    commit_id: str
    removed_paths: tuple[str, ...]
    branch: str
    branch_id: str
    created_branch: bool = False
    cover: CoverOutcome | None = None


@dataclass(frozen=True)
class CommitAttachment:
    id: str
    position: int
    commit_id: str
    role: str
    original_name: str
    media_type: str
    object_hash: str
    size: int
    created_at: str
    updated_at: str
    display_name: str = ""
    description: str = ""


@dataclass(frozen=True)
class PreviewPlan:
    """What registering one preview file would store, computed without writing."""

    source: str
    original_name: str
    media_type: str
    size: int
    object_hash: str
    already_stored: bool
    additional_bytes: int
    requires_confirmation: bool


@dataclass(frozen=True)
class CommitAnnotations:
    commit_id: str
    note: str | None
    note_updated_at: str | None
    labels: tuple[str, ...]


@dataclass(frozen=True)
class GraphCommit:
    branch_id: str
    id: str
    parent_id: str | None
    branch_name: str
    created_at: str
    message: str
    attachments: tuple[CommitAttachment, ...]
    note: str | None
    note_updated_at: str | None
    labels: tuple[str, ...]


@dataclass(frozen=True)
class BranchReference:
    id: str
    name: str
    commit_id: str | None
    comment: str
    current: bool
    created_at: str = ""


@dataclass(frozen=True)
class DeletedBranch:
    id: str
    name: str
    comment: str
    created_at: str
    deleted_at: str


@dataclass(frozen=True)
class HeadPosition:
    branch_id: str
    branch: str
    current_commit: str | None
    at_branch_tip: bool


@dataclass(frozen=True)
class TagReference:
    name: str
    commit_id: str
    comment: str
    created_at: str


@dataclass(frozen=True)
class CommitGraph:
    commits: tuple[GraphCommit, ...]
    branches: tuple[BranchReference, ...]
    tags: tuple[TagReference, ...]
    current_commit: str | None = None
    buds: tuple[Bud, ...] = ()
    deleted_branches: tuple[DeletedBranch, ...] = ()


@dataclass(frozen=True)
class ExportResult:
    commit_id: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class _ArchiveCopy:
    path: str
    item: FileState
    details: dict[str, Any]


@dataclass(frozen=True)
class ArchivePlan:
    """What a static archive would write, computed without writing anything."""

    output: Path
    staging: Path
    commits: int
    files: int
    bytes: int
    free_bytes: int
    removes_incomplete: bool
    texts: dict[str, bytes] = field(repr=False, compare=False)
    copies: tuple[_ArchiveCopy, ...] = field(repr=False, compare=False)

    @property
    def sufficient_space(self) -> bool:
        return self.free_bytes >= self.bytes


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    directory_only: bool


@dataclass(frozen=True)
class Bud:
    branch_id: str
    id: str
    base_commit_id: str | None
    branch_name: str
    created_at: str
    files: tuple[FileState, ...]
    changes: tuple[StatusEntry, ...]
    name: str = ""


@dataclass(frozen=True)
class GoResult:
    commit_id: str
    branch: str
    branch_id: str
    at_branch_tip: bool
    bud: Bud | None
    changes: tuple[StatusEntry, ...]


@dataclass(frozen=True)
class GcResult:
    dry_run: bool
    removed_objects: int
    removed_temps: int
    freed_bytes: int
    objects: tuple[str, ...]
    temps: tuple[str, ...]


@dataclass(frozen=True)
class PruneCommit:
    id: str
    created_at: str
    message: str


@dataclass(frozen=True)
class PruneResult:
    mode: str
    dry_run: bool
    start_tag: str | None
    end_tag: str | None
    commits: tuple[PruneCommit, ...]
    reclaimable_objects: tuple[str, ...]
    reclaimable_bytes: int


@dataclass(frozen=True)
class CommitDeletion:
    """What deleting one commit changes, or would change with dry_run."""

    commit: PruneCommit
    dry_run: bool
    parent_id: str | None
    moved_branches: tuple[BranchReference, ...]
    moved_current: bool
    reconnected_children: tuple[str, ...]
    rebased_buds: tuple[str, ...]
    reclaimable_objects: tuple[str, ...]
    reclaimable_bytes: int


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
    buds: int = 0

    @property
    def dedup_saved_bytes(self) -> int:
        return max(0, self.logical_bytes - self.unique_bytes)


@dataclass
class _MaterializationReceipt:
    committed: bool | None = False


class Repository:
    def __init__(self, root: Path, progress: ProgressCallback | None = None):
        self.root = root.resolve()
        self.control = self.root / CONTROL_DIR
        self.db_path = self.control / DB_NAME
        self.objects = self.control / "objects"
        self.tmp = self.control / "tmp"
        self.worktree_cache = WorktreeCache(self.control / "worktree-cache.db", self.db_path, self._restore_internal)
        self.progress = progress

    @classmethod
    def init(
        cls, path: Path, progress: ProgressCallback | None = None
    ) -> Repository:
        root = path.resolve()
        control = root / CONTROL_DIR
        root.mkdir(parents=True, exist_ok=True)
        try:
            # Directory creation is the atomic claim that prevents concurrent init.
            control.mkdir()
        except FileExistsError as exc:
            raise SproutError(f"already initialized: {root}", code="already_initialized") from exc
        repo = cls(root, progress)
        try:
            repo.objects.mkdir()
            repo.tmp.mkdir()
            with repo.connect() as db:
                db.executescript(SCHEMA)
                db.execute("INSERT INTO meta(key, value) VALUES('schema_version', ?)", (SCHEMA_VERSION,))
                db.execute(
                    "INSERT INTO meta(key, value) VALUES('object_compression', ?)",
                    (OBJECT_COMPRESSION,),
                )
                db.execute("INSERT INTO meta(key, value) VALUES('active_operation', '')")
                db.execute(
                    "INSERT INTO meta(key, value) VALUES('repository_id', ?)",
                    (str(uuid.uuid4()),),
                )
                db.execute(
                    "INSERT INTO meta(key, value) VALUES('repository_created_at', ?)",
                    (utc_timestamp(),),
                )
                db.executemany(
                    "INSERT INTO id_sequences(name) VALUES(?)", ((name,) for name in SEQUENCE_TABLES)
                )
                branch_id = uuid.uuid4().hex
                db.execute(
                    "INSERT INTO branches(id, name, created_at) VALUES(?, 'main', ?)", (branch_id, utc_timestamp())
                )
                db.execute(
                    "INSERT INTO repository_state(id, head_branch_id) VALUES(1, ?)", (branch_id,)
                )
        except Exception:
            shutil.rmtree(control, ignore_errors=True)
            raise
        return repo

    @classmethod
    def discover(
        cls,
        start: Path | None = None,
        progress: ProgressCallback | None = None,
    ) -> Repository:
        current = (start or Path.cwd()).resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if (candidate / CONTROL_DIR / DB_NAME).is_file():
                repo = cls(candidate, progress)
                repo._restore_internal(repo.db_path)
                repo.check_schema()
                # Peek without the repository lock so read-only commands can run
                # while a long write holds it. Recover only when an interrupted
                # operation is recorded; re-check under the lock inside recover.
                with closing(sqlite3.connect(f"{repo.db_path.as_uri()}?mode=ro", uri=True)) as db:
                    row = db.execute(
                        "SELECT value FROM meta WHERE key='active_operation'"
                    ).fetchone()
                if row is None:
                    raise SproutError("repository is missing operation metadata")
                if row[0]:
                    repo._validate_pending_recovery(row[0])
                    with repo.lock():
                        repo._recover_pending_materialization()
                return repo
        raise SproutError("not inside a Sprout project (run 'sprout init')", code="not_initialized")

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

    @staticmethod
    def _schema_metadata_and_tables(
        db: sqlite3.Connection,
    ) -> tuple[dict[str, str], set[str]]:
        metadata = {
            row["key"]: row["value"]
            for row in db.execute("SELECT key, value FROM meta")
        }
        tables = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        return metadata, tables

    @staticmethod
    def _format_error(reason: str, *, code: str = "unsupported_repository_format",
                      details: dict[str, Any] | None = None) -> SproutError:
        return SproutError(
            reason,
            code=code,
            details={"supported_schema_version": SCHEMA_VERSION,
                     **(details or {})},
        )

    def check_schema(self) -> None:
        try:
            # Inspect unsupported repositories without changing their journal mode.
            with closing(sqlite3.connect(f"{self.db_path.as_uri()}?mode=ro", uri=True)) as db:
                db.row_factory = sqlite3.Row
                metadata, tables = self._schema_metadata_and_tables(db)
                actual_schema = dict(
                    db.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL")
                )
        except sqlite3.Error as exc:
            raise self._format_error(f"cannot read repository: {exc}",
                                     details={"reason": "unreadable_metadata"}) from exc
        found_version = metadata.get("schema_version", "missing")
        if found_version != SCHEMA_VERSION:
            raise self._format_error(
                f"unsupported repository schema version: {found_version} (expected {SCHEMA_VERSION})",
                details={"reason": "schema_version", "found_schema_version": found_version},
            )
        missing_tables = sorted(REQUIRED_SCHEMA_TABLES - tables)
        if missing_tables:
            raise self._format_error(
                "repository schema is incomplete; missing tables: " + ", ".join(missing_tables),
                details={"reason": "missing_tables", "missing_tables": missing_tables},
            )
        missing_metadata = sorted(REQUIRED_META_KEYS - metadata.keys())
        if missing_metadata:
            raise self._format_error(
                "repository metadata is incomplete; missing keys: " + ", ".join(missing_metadata),
                details={"reason": "missing_metadata", "missing_keys": missing_metadata},
            )
        if any(actual_schema.get(name) != sql for name, sql in expected_schema().items()):
            raise self._format_error("unsupported or incomplete repository structure",
                                     details={"reason": "schema_structure"})
        with closing(sqlite3.connect(f"{self.db_path.as_uri()}?mode=ro", uri=True)) as db:
            state = db.execute(
                "SELECT s.current_commit_id FROM repository_state s "
                "JOIN branches b ON b.id=s.head_branch_id WHERE s.id=1 AND b.deleted=0"
            ).fetchone()
            invalid_reference = any(
                db.execute(f'PRAGMA foreign_key_check("{table}")').fetchone() is not None
                for table in sorted(REQUIRED_SCHEMA_TABLES)
            )
            if state is None or invalid_reference:
                raise self._format_error("invalid repository state or references",
                                         details={"reason": "invalid_references"})
            counters = {row[0] for row in db.execute("SELECT name FROM id_sequences")}
            if counters != set(SEQUENCE_TABLES):
                raise self._format_error("repository sequence counters are incomplete",
                                         details={"reason": "invalid_sequences"})
        found_compression = metadata["object_compression"]
        if found_compression != OBJECT_COMPRESSION:
            raise self._format_error(
                f"unsupported object compression: {found_compression} (expected {OBJECT_COMPRESSION})",
                details={"reason": "object_compression", "compression": found_compression},
            )
        try:
            uuid.UUID(metadata["repository_id"])
        except (ValueError, AttributeError) as exc:
            raise SproutError("repository has an invalid repository_id") from exc
        try:
            datetime.fromisoformat(metadata["repository_created_at"])
        except ValueError as exc:
            raise SproutError("repository has an invalid repository_created_at") from exc
        if TIMESTAMP_PATTERN.fullmatch(metadata["repository_created_at"]) is None:
            raise SproutError("repository_created_at must be a UTC datetime")

    @contextmanager
    def lock(self) -> Iterator[None]:
        """Acquire the single-writer repository lock without waiting."""
        lock_path = self._restore_internal(self.control / "lock")
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
                raise SproutError(
                    "another Sprout operation is already running",
                    code="repository_locked",
                    details={"retryable": True},
                ) from exc
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
            raise SproutError(f"path is outside the project: {value}", code="path_outside_project", details={"path": str(value)}) from exc
        if not relative.parts or relative.parts[0] == CONTROL_DIR:
            raise SproutError(f"cannot track Sprout metadata: {value}", code="sprout_metadata_path", details={"path": str(value)})
        return relative.as_posix()

    @staticmethod
    def _path_key(path: str) -> str:
        return path_key(path)

    def _relative_destination(self, value: Path) -> str:
        """Resolve a new path while keeping the spelling the user typed for its name."""
        absolute = value if value.is_absolute() else Path.cwd() / value
        if absolute.name in {"", ".", ".."}:
            return self._relative_file(value, must_exist=False)
        try:
            relative = (absolute.parent.resolve(strict=False) / absolute.name).relative_to(self.root)
        except ValueError as exc:
            raise SproutError(f"path is outside the project: {value}", code="path_outside_project", details={"path": str(value)}) from exc
        if relative.parts[0] == CONTROL_DIR:
            raise SproutError(f"cannot track Sprout metadata: {value}", code="sprout_metadata_path", details={"path": str(value)})
        return relative.as_posix()

    def _disk_spellings(self, paths: Iterable[str]) -> dict[str, str | None]:
        """Find how each path is actually spelled on disk; None when it is missing."""
        listings: dict[Path, tuple[set[str], dict[str, list[str]]]] = {}

        def lookup(directory: Path, name: str) -> str | None:
            if directory not in listings:
                try:
                    names = os.listdir(directory)
                except OSError:
                    names = []
                by_key: dict[str, list[str]] = {}
                for item in names:
                    by_key.setdefault(path_key(item), []).append(item)
                listings[directory] = (set(names), by_key)
            exact, by_key = listings[directory]
            if name in exact:
                return name
            matches = by_key.get(path_key(name), [])
            return matches[0] if len(matches) == 1 else None

        result: dict[str, str | None] = {}
        for relative in paths:
            current = self.root
            parts: list[str] = []
            for part in relative.split("/"):
                actual = lookup(current, part)
                if actual is None:
                    parts = []
                    break
                parts.append(actual)
                current = current / actual
            result[relative] = "/".join(parts) if parts and current.is_file() else None
        return result

    def _adopt_disk_spellings(self) -> None:
        """Record spelling-only renames made outside Sprout; the file ID is kept."""
        spellings = self._disk_spellings(self.tracked())
        changed = {old: new for old, new in spellings.items() if new is not None and new != old}
        if not changed:
            return
        with self.connect() as db:
            db.executemany(
                "UPDATE tracked_paths SET path=? WHERE path=?",
                ((new, old) for old, new in changed.items()),
            )
        self.worktree_cache.invalidate([*changed, *changed.values()])

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
                raise SproutError(f"symbolic links are not supported: {value}", code="symlink_not_supported", details={"path": str(value)})
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
                raise SproutError(f"file or directory does not exist: {value}", code="path_not_found", details={"path": str(value)})
        with self.connect() as db:
            existing = {path_key(row[0]): row[0] for row in db.execute("SELECT path FROM tracked_paths")}
            final = dict(existing)
            added: list[str] = []
            respelled: dict[str, str] = {}
            for path in sorted(paths):
                key = path_key(path)
                current = final.get(key)
                if current == path:
                    continue
                if current is None:
                    added.append(path)
                elif current in existing.values() and self._same_working_file(current, path):
                    respelled[current] = path
                else:
                    raise SproutError(
                        f"path conflicts with {current}: {path}",
                        code="path_case_conflict",
                        details={"path": path, "conflicting_path": current},
                    )
                final[key] = path
            reject_path_conflicts(final.values())
            db.executemany(
                "UPDATE tracked_paths SET path=? WHERE path=?",
                ((new, old) for old, new in respelled.items()),
            )
            for path in added:
                file_id = uuid.uuid4().hex
                db.execute("INSERT INTO file_identities(id) VALUES(?)", (file_id,))
                db.execute(
                    "INSERT INTO tracked_paths(path,path_key,file_id) VALUES(?,?,?)",
                    (path, path_key(path), file_id),
                )
        self.worktree_cache.invalidate([*paths, *respelled])
        return sorted(paths)

    def _same_working_file(self, tracked: str, candidate: str) -> bool:
        """Tell a respelled file from a second file that differs only by spelling."""
        old, new = self.root / Path(tracked), self.root / Path(candidate)
        return not old.exists() or (new.exists() and os.path.samefile(old, new))

    @locked
    def untrack(self, values: list[Path]) -> list[str]:
        requested: list[str] = []
        with self.connect() as db:
            tracked = [row[0] for row in db.execute("SELECT path FROM tracked_paths")]
            for value in values:
                relative = self._relative_file(value, must_exist=False)
                relative_key = self._path_key(relative)
                prefix_key = relative_key.rstrip("/") + "/"
                requested.extend(
                    path
                    for path in tracked
                    if self._path_key(path) == relative_key
                    or self._path_key(path).startswith(prefix_key)
                )
            db.executemany("DELETE FROM tracked_paths WHERE path=?", ((p,) for p in set(requested)))
        self.worktree_cache.invalidate(requested)
        return sorted(set(requested))

    @locked
    def move(self, source: Path, destination: Path) -> tuple[str, str]:
        source_input = source if source.is_absolute() else Path.cwd() / source
        if source_input.is_symlink():
            raise SproutError(f"symbolic links are not supported: {source}")
        if not source_input.exists():
            raise SproutError(f"file does not exist: {source}")
        self._adopt_disk_spellings()
        source_relative = self._relative_file(source)
        tracked = self.tracked()
        if source_relative not in tracked:
            raise SproutError(f"path is not tracked: {source}")
        source_absolute = self.root / Path(source_relative)
        if not source_absolute.is_file():
            raise SproutError(f"tracked path is not a file: {source}")

        destination_relative = self._relative_destination(destination)
        destination_absolute = self.root / Path(destination_relative)
        respelling = (
            destination_relative != source_relative
            and path_key(destination_relative) == path_key(source_relative)
        )
        if destination_absolute.exists() and not (
            respelling and os.path.samefile(source_absolute, destination_absolute)
        ):
            raise SproutError(f"destination already exists: {destination}")
        if destination_absolute.is_symlink():
            raise SproutError(f"symbolic links are not supported: {destination}")
        others = tracked - {source_relative}
        if path_key(destination_relative) in {path_key(path) for path in others}:
            raise SproutError(f"destination is already tracked: {destination}")
        reject_path_conflicts(others | {destination_relative})

        destination_absolute.parent.mkdir(parents=True, exist_ok=True)
        self._rename_file(source_absolute, destination_absolute, respelling=respelling)
        try:
            with self.connect() as db:
                db.execute(
                    "UPDATE tracked_paths SET path=?, path_key=? WHERE path=?",
                    (destination_relative, path_key(destination_relative), source_relative),
                )
        except Exception:
            if destination_absolute.is_file() and (respelling or not source_absolute.exists()):
                source_absolute.parent.mkdir(parents=True, exist_ok=True)
                self._rename_file(destination_absolute, source_absolute, respelling=respelling)
            raise
        self.worktree_cache.invalidate([source_relative, destination_relative])
        return source_relative, destination_relative

    @staticmethod
    def _rename_file(source: Path, destination: Path, *, respelling: bool) -> None:
        """Rename a file; a spelling-only change goes through a temporary name."""
        if not respelling:
            os.replace(source, destination)
            return
        temporary = destination.with_name(f".sprout-rename-{uuid.uuid4().hex}")
        os.replace(source, temporary)
        try:
            os.replace(temporary, destination)
        except OSError:
            os.replace(temporary, source)
            raise

    def tracked(self) -> set[str]:
        with self.connect() as db:
            return {row[0] for row in db.execute("SELECT path FROM tracked_paths")}

    def tracked_ids(self) -> dict[str, str]:
        with self.connect() as db:
            return dict(db.execute("SELECT path,file_id FROM tracked_paths"))

    def tracking_status(self, values: list[Path]) -> list[tuple[str, bool]]:
        """Return tracked state for files, or tracked descendants for directories."""
        tracked = self.tracked()
        tracked_keys = {path_key(path) for path in tracked}
        results: dict[str, bool] = {}
        for value in values:
            relative = self._relative_file(value, must_exist=False)
            absolute = self.root / Path(relative)
            prefix = path_key(relative.rstrip("/") + "/")
            if absolute.is_dir():
                descendants = sorted(path for path in tracked if path_key(path).startswith(prefix))
                for path in descendants:
                    results[path] = True
                if not descendants:
                    results[relative + "/"] = False
            else:
                results[relative] = path_key(relative) in tracked_keys
        return sorted(results.items())

    def untracked_files(self) -> list[str]:
        """List regular project files that are not registered for commits."""
        tracked = {path_key(path) for path in self.tracked()}
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
                if path_key(normalized) in tracked:
                    continue
                if self._is_ignored(normalized, rules):
                    continue
                result.append(normalized)
        return sorted(result)

    @staticmethod
    def hash_file(
        path: Path,
        progress: ProgressCallback | None = None,
        label: str | None = None,
    ) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        total = path.stat().st_size
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(IO_CHUNK_SIZE), b""):
                digest.update(chunk)
                size += len(chunk)
                if progress is not None:
                    progress(label or path.name, size, total)
        return digest.hexdigest(), size

    @staticmethod
    def _file_signature(info: os.stat_result) -> dict[str, Any]:
        return {
            "size": info.st_size,
            "mtime_ns": info.st_mtime_ns,
            "ctime_ns": info.st_ctime_ns,
            "file_id": f"{info.st_dev}:{info.st_ino}",
        }

    def _hash_worktree_files(
        self, relatives: Iterable[str], *, progress: bool = True
    ) -> dict[str, tuple[str, int]]:
        """Hash present working files, skipping files whose observed metadata is unchanged.

        A cached hash is reused only when size, times and file identity all match and
        the file was last modified at least RACY_MARGIN_NS before it was observed. A
        later rewrite then always lands in a newer timestamp granule, so it cannot keep
        the recorded modification time. Anything else is hashed again.
        """
        relatives = sorted(relatives)
        if not relatives:
            return {}
        cached = self.worktree_cache.lookup(relatives)
        result: dict[str, tuple[str, int]] = {}
        observed: list[dict[str, Any]] = []
        for relative in relatives:
            path = self.root / Path(relative)
            recorded_ns = time.time_ns()
            signature = self._file_signature(path.stat())
            row = cached.get(relative)
            if (
                row is not None
                and all(row[key] == value for key, value in signature.items())
                and row["recorded_ns"] - row["mtime_ns"] >= RACY_MARGIN_NS
            ):
                result[relative] = (row["object_hash"], row["size"])
                continue
            digest, size = self.hash_file(path, self.progress if progress else None, relative)
            result[relative] = (digest, size)
            # A file that changed while it was read is hashed again next time.
            if size == signature["size"] and self._file_signature(path.stat()) == signature:
                observed.append(
                    {"path": relative, **signature, "object_hash": digest, "recorded_ns": recorded_ns}
                )
        self.worktree_cache.record(observed)
        return result

    @staticmethod
    def _branch_id_from_db(db: sqlite3.Connection, name: str) -> str:
        row = db.execute("SELECT id FROM branches WHERE name=? AND deleted=0", (name,)).fetchone()
        if row is None:
            raise SproutError(f"unknown branch: {name}", code="unknown_branch", details={"name": name})
        return row[0]

    def branch_id(self, name: str | None = None) -> str:
        with self.connect() as db:
            if name is not None:
                return self._branch_id_from_db(db, name)
            return db.execute("SELECT head_branch_id FROM repository_state WHERE id=1").fetchone()[0]

    def head_branch(self) -> str:
        with self.connect() as db:
            return db.execute(
                "SELECT b.name FROM branches b JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()[0]

    def head_commit(self) -> str | None:
        with self.connect() as db:
            return db.execute(
                "SELECT b.commit_id FROM branches b JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()[0]

    @staticmethod
    def _current_commit_from_db(db: sqlite3.Connection) -> str | None:
        row = db.execute("SELECT current_commit_id FROM repository_state WHERE id=1").fetchone()
        if row is None:
            raise SproutError("repository is missing current position")
        return row[0]

    @staticmethod
    def _set_current_commit(db: sqlite3.Connection, commit_id: str | None) -> None:
        db.execute("UPDATE repository_state SET current_commit_id=? WHERE id=1", (commit_id,))

    def current_commit(self) -> str | None:
        """Return the snapshot the working tree is based on, or its initial empty state."""
        with self.connect() as db:
            return self._current_commit_from_db(db)

    def current_position(self) -> tuple[str | None, bool]:
        """Return the current snapshot and whether it is the current branch tip."""
        with self.connect() as db:
            db.execute("BEGIN")
            current = self._current_commit_from_db(db)
            tip = db.execute(
                "SELECT b.commit_id FROM branches b JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()[0]
            return current, current == tip

    def head_position(self) -> HeadPosition:
        """Read the current branch and snapshot from one SQLite snapshot."""
        with self.connect() as db:
            db.execute("BEGIN")
            current = self._current_commit_from_db(db)
            row = db.execute(
                "SELECT b.id, b.name, b.commit_id FROM branches b "
                "JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()
            return HeadPosition(row["id"], row["name"], current, current == row["commit_id"])

    @staticmethod
    def _validate_file_time(value: Any, path: str) -> None:
        # Signed nanoseconds: zero and pre-epoch timestamps are valid metadata.
        # SQLite INTEGER enforces the signed 64-bit storage range.
        if type(value) is not int:
            raise SproutError(
                f"invalid saved file time: {path}", code="invalid_file_time",
                details={"path": path},
            )

    @staticmethod
    def _manifest_from_db(db: sqlite3.Connection, commit_id: str | None) -> dict[str, FileState]:
        if commit_id is None:
            return {}
        result: dict[str, FileState] = {}
        for row in db.execute(
            "SELECT path, object_hash, size, mtime_ns, file_id FROM commit_files WHERE commit_id=? ORDER BY path",
            (commit_id,),
        ):
            Repository._validate_file_time(row["mtime_ns"], row["path"])
            result[row["path"]] = FileState(
                row["path"], row["object_hash"], row["size"], row["mtime_ns"], row["file_id"]
            )
        return result

    def manifest(self, commit_id: str | None) -> dict[str, FileState]:
        with self.connect() as db:
            return self._manifest_from_db(db, commit_id)

    def status(self) -> list[StatusEntry]:
        bindings = self._spelled_bindings()
        head = self.manifest(self.current_commit())
        head_by_key = {path_key(path): path for path in head}
        present = {relative for relative in bindings if (self.root / Path(relative)).is_file()}
        hashes = self._hash_worktree_files(
            relative for relative in present if path_key(relative) in head_by_key
        )
        result: list[StatusEntry] = []
        matched: set[str] = set()
        for relative in sorted(bindings):
            saved = head_by_key.get(path_key(relative))
            if saved is not None:
                matched.add(saved)
            if relative not in present:
                if saved is not None:
                    result.append(StatusEntry("deleted", saved))
                continue
            if saved is None:
                result.append(StatusEntry("added", relative))
                continue
            if saved != relative:
                result.append(StatusEntry("renamed", relative, saved))
                continue
            digest, size = hashes[relative]
            if (digest != head[saved].object_hash or size != head[saved].size
                    or bindings[relative] != head[saved].file_id):
                result.append(StatusEntry("modified", relative))
        result.extend(StatusEntry("deleted", path) for path in set(head) - matched)
        return sorted(result, key=lambda entry: entry.path)

    def _spelled_bindings(self) -> dict[str, str]:
        """Tracked paths and IDs as they are spelled on disk now, without recording it."""
        bindings = self.tracked_ids()
        spellings = self._disk_spellings(bindings)
        return {spellings[path] or path: file_id for path, file_id in bindings.items()}

    @staticmethod
    def diff_manifests(
        before: dict[str, FileState], after: dict[str, FileState]
    ) -> list[DiffEntry]:
        result: list[DiffEntry] = []
        before_keys = {path_key(path): item for path, item in before.items()}
        after_keys = {path_key(path): item for path, item in after.items()}
        for key in before_keys.keys() | after_keys.keys():
            left = before_keys.get(key)
            right = after_keys.get(key)
            if left is not None and right is not None and (
                left.path == right.path or left.file_id == right.file_id
            ):
                if left.path != right.path:
                    result.append(DiffEntry("renamed", right.path, left.size, right.size, left.path))
                elif left.object_hash != right.object_hash or left.size != right.size or left.file_id != right.file_id:
                    result.append(DiffEntry("modified", right.path, left.size, right.size))
                continue
            if right is not None:
                result.append(DiffEntry("added", right.path, None, right.size))
            if left is not None:
                result.append(DiffEntry("deleted", left.path, left.size, None))
        return sorted(result, key=lambda entry: entry.path)

    def _working_tree_manifest(self) -> dict[str, FileState]:
        bindings = self._spelled_bindings()
        present = (relative for relative in bindings if (self.root / Path(relative)).is_file())
        return {
            relative: FileState(relative, digest, size, 0, bindings[relative])
            for relative, (digest, size) in self._hash_worktree_files(present).items()
        }

    def diff(
        self, commit_a: str | None = None, commit_b: str | None = None
    ) -> list[DiffEntry]:
        if commit_a is None and commit_b is None:
            before = self.manifest(self.current_commit())
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
        total = source.stat().st_size
        try:
            label = source.relative_to(self.root).as_posix()
        except ValueError:
            label = source.name
        try:
            with os.fdopen(fd, "wb") as target, source.open("rb") as input_file:
                compressor = zstandard.ZstdCompressor(level=OBJECT_COMPRESSION_LEVEL)
                with compressor.stream_writer(target, closefd=False) as compressed:
                    for chunk in iter(lambda: input_file.read(IO_CHUNK_SIZE), b""):
                        digest.update(chunk)
                        size += len(chunk)
                        compressed.write(chunk)
                        if self.progress is not None:
                            self.progress(label, size, total)
                target.flush()
                os.fsync(target.fileno())
            object_hash = digest.hexdigest()
            destination = self.objects / object_hash[:2] / object_hash
            destination.parent.mkdir(exist_ok=True)
            self._check_object_encoding(object_hash)
            if destination.exists():
                try:
                    existing_hash, existing_size = self._read_object(destination)
                except SproutError as exc:
                    raise SproutError(
                        f"corrupt object already exists: {object_hash}"
                    ) from exc
                if existing_hash != object_hash or existing_size != size:
                    raise SproutError(f"corrupt object already exists: {object_hash}")
                Path(temp_name).unlink()
            else:
                os.replace(temp_name, destination)
            return object_hash, size
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise

    def _object_path(self, object_hash: str) -> Path:
        return self.objects / object_hash[:2] / object_hash

    def _register_objects(
        self, db: sqlite3.Connection, objects: dict[str, int], created_at: str
    ) -> None:
        """Record stored object files in the same transaction that references them."""
        for object_hash in objects:
            self._check_object_encoding(object_hash, db)
        db.executemany(
            "INSERT INTO objects(hash, size, stored_size, encoding, created_at) "
            "VALUES(?, ?, ?, ?, ?) ON CONFLICT(hash) DO NOTHING",
            (
                (
                    object_hash,
                    size,
                    self._object_path(object_hash).stat().st_size,
                    OBJECT_COMPRESSION,
                    created_at,
                )
                for object_hash, size in sorted(objects.items())
            ),
        )

    def _check_object_encoding(self, object_hash: str, db: sqlite3.Connection | None = None) -> None:
        if db is None:
            with self.connect() as connection:
                self._check_object_encoding(object_hash, connection)
            return
        row = db.execute("SELECT encoding FROM objects WHERE hash=?", (object_hash,)).fetchone()
        if row is not None and row[0] != OBJECT_COMPRESSION:
            raise SproutError(
                f"unsupported object encoding {row[0]!r}: {object_hash}",
                code="unsupported_object_encoding",
                details={"object_hash": object_hash, "encoding": row[0]},
            )

    @staticmethod
    def _read_object(
        source: Path,
        target: BinaryIO | None = None,
        progress: ProgressCallback | None = None,
        label: str | None = None,
        total: int = 0,
    ) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        try:
            with source.open("rb") as compressed:
                reader = zstandard.ZstdDecompressor().stream_reader(compressed)
                with reader:
                    for chunk in iter(lambda: reader.read(IO_CHUNK_SIZE), b""):
                        digest.update(chunk)
                        size += len(chunk)
                        if target is not None:
                            target.write(chunk)
                        if progress is not None:
                            progress(label or source.name, size, total)
        except (OSError, zstandard.ZstdError) as exc:
            raise SproutError(f"cannot read compressed object: {source.name}") from exc
        return digest.hexdigest(), size

    def _copy_verified_object(self, item: FileState, target: BinaryIO | None = None) -> None:
        self._check_object_encoding(item.object_hash)
        source = self.objects / item.object_hash[:2] / item.object_hash
        if not source.is_file():
            raise SproutError(f"missing object {item.object_hash} for {item.path}")
        try:
            digest, size = self._read_object(
                source,
                target,
                self.progress,
                item.path,
                item.size,
            )
        except SproutError as exc:
            raise SproutError(f"corrupt object {item.object_hash} for {item.path}") from exc
        if digest != item.object_hash or size != item.size:
            raise SproutError(f"corrupt object {item.object_hash} for {item.path}")

    def _prepare_thumbnail(
        self, source: Path
    ) -> tuple[str, str, str, int]:
        original_name = source.name
        try:
            resolved = source.resolve(strict=True)
        except OSError as exc:
            raise SproutError(f"thumbnail file does not exist: {source}", code="thumbnail_not_found", details={"path": str(source)}) from exc
        if not resolved.is_file():
            raise SproutError(f"thumbnail is not a file: {source}", code="thumbnail_not_file", details={"path": str(source)})
        before = resolved.stat()
        if before.st_size > THUMBNAIL_MAX_BYTES:
            raise SproutError(
                f"thumbnail exceeds {THUMBNAIL_MAX_BYTES} byte limit: {before.st_size}",
                code="thumbnail_too_large",
                details={"limit": THUMBNAIL_MAX_BYTES},
            )
        try:
            with Image.open(resolved) as image:
                media_type = THUMBNAIL_MEDIA_TYPES.get(image.format or "")
                if media_type is None:
                    raise SproutError(
                        "unsupported thumbnail format; use PNG, JPEG, or WebP",
                        code="unsupported_thumbnail",
                    )
                width, height = image.size
                if width > THUMBNAIL_MAX_DIMENSION or height > THUMBNAIL_MAX_DIMENSION:
                    raise SproutError(
                        "thumbnail dimensions exceed "
                        f"{THUMBNAIL_MAX_DIMENSION}x{THUMBNAIL_MAX_DIMENSION}: "
                        f"{width}x{height}",
                        code="thumbnail_too_large",
                        details={"max_dimension": THUMBNAIL_MAX_DIMENSION},
                    )
                if getattr(image, "n_frames", 1) != 1:
                    raise SproutError("animated images cannot be used as thumbnails", code="animated_thumbnail")
                image.load()
        except SproutError:
            raise
        except (
            Image.DecompressionBombError,
            UnidentifiedImageError,
            OSError,
            SyntaxError,
            ValueError,
        ) as exc:
            raise SproutError(f"invalid thumbnail image: {source}", code="invalid_thumbnail", details={"path": str(source)}) from exc

        object_hash, size = self._store_object(resolved)
        after = resolved.stat()
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or size != after.st_size
        ):
            raise SproutError(f"thumbnail changed while reading: {source}", code="file_changed", details={"path": str(source)})
        return original_name, media_type, object_hash, size

    @staticmethod
    def _render_cover(source: Path, directory: Path) -> tuple[Path | None, str | None]:
        """Write a bounded thumbnail of an image, or return why it cannot be made."""
        try:
            if source.stat().st_size > COVER_MAX_BYTES:
                return None, "cover_too_large"
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(source) as image:
                    if image.format not in COVER_FORMATS:
                        return None, "cover_not_image"
                    if image.size[0] * image.size[1] > COVER_MAX_PIXELS:
                        return None, "cover_too_large"
                    if getattr(image, "n_frames", 1) != 1:
                        return None, "cover_animated"
                    image.load()
                    oriented = ImageOps.exif_transpose(image)
                    if oriented.mode in {"I", "I;16", "I;16L", "I;16B"}:
                        # PNG integer grayscale samples use the full 16-bit range.
                        # Direct RGB conversion clips everything above 255 to white.
                        oriented = oriented.convert("I").point(lambda value: value / 257 + 0.5).convert("L")
                    oriented.thumbnail((COVER_SIDE, COVER_SIDE), Image.Resampling.LANCZOS)
                    if oriented.mode in {"RGBA", "LA", "PA"} or "transparency" in oriented.info:
                        output = directory / "cover.png"
                        oriented.convert("RGBA").save(output, format="PNG")
                    else:
                        output = directory / "cover.jpg"
                        oriented.convert("RGB").save(output, format="JPEG", quality=85)
                    return output, None
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            return None, "cover_too_large"
        except UnidentifiedImageError:
            return None, "cover_not_image"
        except (OSError, SyntaxError, ValueError):
            return None, "cover_unreadable"

    def _prepare_cover(self, source: Path, name: str) -> tuple[tuple[str, str, str, int] | None, str | None]:
        with tempfile.TemporaryDirectory(prefix="sprout-cover-") as directory:
            rendered, reason = self._render_cover(source, Path(directory))
            if rendered is None:
                return None, reason
            object_hash, size = self._store_object(rendered)
            media_type = "image/png" if rendered.suffix == ".png" else "image/jpeg"
            return (Path(name).stem + rendered.suffix, media_type, object_hash, size), None

    def _cover_thumbnail(
        self, files: list[FileState]
    ) -> tuple[tuple[str, str, str, int] | None, CoverOutcome | None]:
        """Make a save's thumbnail from the cover file; failing here never fails the save."""
        file_id = self.cover_file()[0]
        if file_id is None:
            return None, None
        item = next((state for state in files if state.file_id == file_id), None)
        if item is None:
            return None, CoverOutcome(False, "cover_missing")
        prepared, reason = self._prepare_cover(self.root / Path(item.path), Path(item.path).name)
        return prepared, CoverOutcome(prepared is not None, reason)

    def cover_file(self) -> tuple[str | None, str | None]:
        """Return the cover's file ID and its tracked path; the path is None once untracked."""
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (COVER_META_KEY,)).fetchone()
            if row is None:
                return None, None
            path = db.execute("SELECT path FROM tracked_paths WHERE file_id=?", (row[0],)).fetchone()
            return row[0], path[0] if path else None

    @locked
    def set_cover(self, value: Path) -> tuple[str, str, str | None]:
        """Choose a tracked file as the cover; also say if it cannot make a thumbnail now."""
        self._adopt_disk_spellings()
        relative = self._relative_file(value, must_exist=False)
        with self.connect() as db:
            row = db.execute(
                "SELECT path, file_id FROM tracked_paths WHERE path_key=?", (path_key(relative),)
            ).fetchone()
            if row is None:
                raise SproutError(f"path is not tracked: {value}", code="cover_not_tracked", details={"path": relative})
            db.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (COVER_META_KEY, row["file_id"]),
            )
        with tempfile.TemporaryDirectory(prefix="sprout-cover-") as directory:
            _rendered, problem = self._render_cover(self.root / Path(row["path"]), Path(directory))
        return row["file_id"], row["path"], problem

    @locked
    def clear_cover(self) -> None:
        with self.connect() as db:
            db.execute("DELETE FROM meta WHERE key=?", (COVER_META_KEY,))

    @locked
    def apply_cover(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Give leaves without a thumbnail one from the cover; existing thumbnails stay."""
        file_id = self.cover_file()[0]
        if file_id is None:
            raise SproutError("no cover file is set", code="cover_not_set")
        with self.connect() as db:
            rows = list(db.execute(
                "SELECT c.id, f.path, f.object_hash, f.size, "
                "EXISTS(SELECT 1 FROM commit_attachments a WHERE a.commit_id=c.id AND a.role=?) AS has_thumbnail "
                "FROM commits c LEFT JOIN commit_files f ON f.commit_id=c.id AND f.file_id=? ORDER BY c.seq",
                (THUMBNAIL_ROLE, file_id),
            ))
        applied: list[tuple[str, tuple[str, str, str, int] | None]] = []
        skipped: list[dict[str, str]] = []
        kept = 0
        made: dict[str, tuple[tuple[str, str, str, int] | None, str | None]] = {}
        with tempfile.TemporaryDirectory(prefix="sprout-cover-") as directory:
            for row in rows:
                if row["has_thumbnail"]:
                    kept += 1
                    continue
                if row["path"] is None:
                    skipped.append({"commit_id": row["id"], "reason": "cover_missing"})
                    continue
                if row["object_hash"] not in made:
                    source = Path(directory) / row["object_hash"]
                    try:
                        with source.open("wb") as target:
                            self._copy_verified_object(
                                FileState(row["path"], row["object_hash"], row["size"], 0), target
                            )
                    except (OSError, SproutError):
                        made[row["object_hash"]] = (None, "cover_unreadable")
                    else:
                        if dry_run:
                            scratch = Path(directory) / f"{row['object_hash']}-render"
                            scratch.mkdir()
                            made[row["object_hash"]] = (None, self._render_cover(source, scratch)[1])
                        else:
                            made[row["object_hash"]] = self._prepare_cover(source, Path(row["path"]).name)
                prepared, reason = made[row["object_hash"]]
                if reason is not None:
                    skipped.append({"commit_id": row["id"], "reason": reason})
                else:
                    applied.append((row["id"], prepared))
        if not dry_run and applied:
            now = utc_timestamp()
            with self.connect() as db:
                self._register_objects(db, {item[2]: item[3] for _id, item in applied}, now)
                db.executemany(
                    "INSERT INTO commit_attachments(id, commit_id, role, original_name, media_type, object_hash, size, "
                    "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        (uuid.uuid4().hex, commit_id, THUMBNAIL_ROLE, *item, now, now)
                        for commit_id, item in applied
                    ),
                )
        return {
            "dry_run": dry_run,
            "applied": [commit_id for commit_id, _item in applied],
            "skipped": skipped,
            "kept": kept,
        }

    @staticmethod
    def _attachment_from_row(row: sqlite3.Row) -> CommitAttachment:
        return CommitAttachment(
            id=row["id"],
            position=row["position"],
            commit_id=row["commit_id"],
            role=row["role"],
            original_name=row["original_name"],
            media_type=row["media_type"],
            object_hash=row["object_hash"],
            size=row["size"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            display_name=row["display_name"], description=row["description"],
        )

    def _store_tracked_files(self, action: str) -> tuple[list[FileState], list[str]]:
        """Store every present tracked file and list tracked paths that are missing."""
        self._adopt_disk_spellings()
        identities = self.tracked_ids()
        files: list[FileState] = []
        missing: list[str] = []
        for relative in sorted(self.tracked()):
            path = self.root / Path(relative)
            if not path.is_file():
                missing.append(relative)
                continue
            before = path.stat()
            object_hash, size = self._store_object(path)
            after = path.stat()
            if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
                raise SproutError(f"file changed while {action}: {relative}", code="file_changed", details={"path": str(relative)})
            files.append(FileState(relative, object_hash, size, after.st_mtime_ns, identities[relative]))
        return files, missing

    @locked
    def commit(self, message: str, thumbnail: Path | None = None) -> CommitResult:
        if not message.strip():
            raise SproutError("commit message cannot be empty", code="empty_message")
        files, missing = self._store_tracked_files("committing")

        parent = self.current_commit()
        previous = self.manifest(parent)
        current = {item.path: item for item in files}
        content_signature = lambda manifest: {
            path: (state.object_hash, state.size, state.file_id) for path, state in manifest.items()
        }
        if parent is not None and content_signature(current) == content_signature(previous):
            raise SproutError("nothing to commit", code="nothing_to_commit")
        if parent is None and not files:
            raise SproutError("nothing to commit", code="nothing_to_commit")
        cover: CoverOutcome | None = None
        if thumbnail is not None:
            prepared_thumbnail = self._prepare_thumbnail(thumbnail)
        else:
            prepared_thumbnail, cover = self._cover_thumbnail(files)
        commit_id = uuid.uuid4().hex
        branch = self.head_branch()
        now = datetime.now(timezone.utc)
        created_at = utc_timestamp(now)
        stored = {item.object_hash: item.size for item in files}
        if prepared_thumbnail is not None:
            stored[prepared_thumbnail[2]] = prepared_thumbnail[3]
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._register_objects(db, stored, created_at)
            tip = db.execute("SELECT commit_id FROM branches WHERE name=? AND deleted=0", (branch,)).fetchone()
            # Saving on top of a non-tip snapshot grows a new branch from it.
            created_branch = tip is None or tip[0] != parent
            if created_branch:
                branch = self._auto_branch_name(db, now)
                db.execute(
                    "INSERT INTO branches(id, name, commit_id, comment, created_at) VALUES(?, ?, NULL, '', ?)",
                    (uuid.uuid4().hex, branch, created_at),
                )
                db.execute("UPDATE repository_state SET head_branch_id=? WHERE id=1", (self._branch_id_from_db(db, branch),))
            db.execute(
                "INSERT INTO commits(id, seq, parent_id, branch_id, branch_name, created_at, message) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    commit_id, recovery.next_seq(db, "commits"), parent,
                    self._branch_id_from_db(db, branch), branch, created_at, message.strip(),
                ),
            )
            db.executemany(
                "INSERT INTO commit_files(commit_id, path, path_key, object_hash, size, mtime_ns, file_id) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    (commit_id, item.path, path_key(item.path), item.object_hash, item.size, item.mtime_ns, item.file_id)
                    for item in files
                ),
            )
            if prepared_thumbnail is not None:
                original_name, media_type, object_hash, size = prepared_thumbnail
                db.execute(
                    "INSERT INTO commit_attachments("
                    "id, commit_id, role, original_name, media_type, object_hash, size, "
                    "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uuid.uuid4().hex,
                        commit_id,
                        THUMBNAIL_ROLE,
                        original_name,
                        media_type,
                        object_hash,
                        size,
                        created_at,
                        created_at,
                    ),
                )
            db.execute("UPDATE branches SET commit_id=? WHERE name=? AND deleted=0", (commit_id, branch))
            self._set_current_commit(db, commit_id)
            db.executemany("DELETE FROM tracked_paths WHERE path=?", ((p,) for p in missing))
            branch_id = self._branch_id_from_db(db, branch)
        self.worktree_cache.invalidate(missing)
        return CommitResult(commit_id, tuple(missing), branch, branch_id, created_branch, cover)

    @staticmethod
    def _auto_branch_name(db: sqlite3.Connection, now: datetime) -> str:
        """Return an unused branch name such as branch-20261028-153000."""
        base = "branch-" + now.astimezone().strftime("%Y%m%d-%H%M%S")
        taken = {
            row[0] for row in db.execute("SELECT name FROM branches WHERE deleted=0 UNION SELECT name FROM tags")
        }
        name, suffix = base, 2
        while name in taken:
            name, suffix = f"{base}-{suffix}", suffix + 1
        return name

    def resolve_commit(self, value: str) -> str:
        if not value.strip():
            raise SproutError("commit id required", code="commit_id_required")
        with self.connect() as db:
            branch = db.execute("SELECT commit_id FROM branches WHERE name=? AND deleted=0", (value,)).fetchone()
            if branch is not None:
                if branch[0] is None:
                    raise SproutError(f"branch has no commits: {value}", code="branch_has_no_commits", details={"name": value})
                return branch[0]
            tag = db.execute("SELECT commit_id FROM tags WHERE name=?", (value,)).fetchone()
            if tag is not None:
                return tag[0]
            if HEX_COMMIT_REFERENCE.fullmatch(value) is None:
                raise SproutError(f"unknown commit: {value}", code="unknown_commit", details={"commit_id": value})
            rows = db.execute("SELECT id FROM commits WHERE id LIKE ?", (value + "%",)).fetchall()
        if not rows:
            raise SproutError(f"unknown commit: {value}", code="unknown_commit", details={"commit_id": value})
        if len(rows) > 1:
            raise SproutError(f"ambiguous commit prefix: {value}", code="ambiguous_commit", details={"commit_id": value})
        return rows[0][0]

    def commit_info(self, value: str) -> tuple[sqlite3.Row, list[FileState]]:
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            row = db.execute("SELECT * FROM commits WHERE id=?", (commit_id,)).fetchone()
        return row, list(self.manifest(commit_id).values())

    @staticmethod
    def _empty_annotations(commit_id: str) -> CommitAnnotations:
        return CommitAnnotations(commit_id, None, None, ())

    def annotations(self, value: str) -> CommitAnnotations:
        commit_id = self.resolve_commit(value)
        return self.annotations_many([commit_id])[commit_id]

    @classmethod
    def _annotations_many_from_db(
        cls, db: sqlite3.Connection, commit_ids: list[str]
    ) -> dict[str, CommitAnnotations]:
        unique_ids = list(dict.fromkeys(commit_ids))
        result = {
            commit_id: cls._empty_annotations(commit_id)
            for commit_id in unique_ids
        }
        if not unique_ids:
            return result

        notes: dict[str, tuple[str, str]] = {}
        labels: dict[str, list[str]] = {commit_id: [] for commit_id in unique_ids}
        for offset in range(0, len(unique_ids), 900):
            chunk = unique_ids[offset : offset + 900]
            placeholders = ",".join("?" for _ in chunk)
            for row in db.execute(
                f"SELECT commit_id, note, updated_at FROM commit_notes "
                f"WHERE commit_id IN ({placeholders})",
                chunk,
            ):
                notes[row["commit_id"]] = (row["note"], row["updated_at"])
            for row in db.execute(
                f"SELECT commit_id, label FROM commit_labels "
                f"WHERE commit_id IN ({placeholders}) ORDER BY label",
                chunk,
            ):
                labels[row["commit_id"]].append(row["label"])

        for commit_id in unique_ids:
            note = notes.get(commit_id)
            result[commit_id] = CommitAnnotations(
                commit_id=commit_id,
                note=note[0] if note is not None else None,
                note_updated_at=note[1] if note is not None else None,
                labels=tuple(labels[commit_id]),
            )
        return result

    def annotations_many(
        self, commit_ids: list[str]
    ) -> dict[str, CommitAnnotations]:
        with self.connect() as db:
            return self._annotations_many_from_db(db, commit_ids)

    @classmethod
    def _attachments_many_from_db(
        cls, db: sqlite3.Connection, commit_ids: list[str]
    ) -> dict[str, tuple[CommitAttachment, ...]]:
        unique_ids = list(dict.fromkeys(commit_ids))
        grouped: dict[str, list[CommitAttachment]] = {
            commit_id: [] for commit_id in unique_ids
        }
        for offset in range(0, len(unique_ids), 900):
            chunk = unique_ids[offset : offset + 900]
            placeholders = ",".join("?" for _ in chunk)
            for row in db.execute(
                f"SELECT * FROM commit_attachments "
                f"WHERE commit_id IN ({placeholders}) ORDER BY role, position, id",
                chunk,
            ):
                grouped[row["commit_id"]].append(cls._attachment_from_row(row))
        return {
            commit_id: tuple(attachments)
            for commit_id, attachments in grouped.items()
        }

    def attachments_many(
        self, commit_ids: list[str]
    ) -> dict[str, tuple[CommitAttachment, ...]]:
        with self.connect() as db:
            return self._attachments_many_from_db(db, commit_ids)

    def commit_graph(self) -> CommitGraph:
        """Return every commit and current reference in one read transaction."""
        with self.connect() as db:
            db.execute("BEGIN")
            commit_rows = list(
                db.execute(
                    "SELECT * FROM commits ORDER BY seq DESC"
                )
            )
            commit_ids = [row["id"] for row in commit_rows]
            annotations = self._annotations_many_from_db(db, commit_ids)
            attachments = self._attachments_many_from_db(db, commit_ids)
            current_branch = db.execute(
                "SELECT b.name FROM branches b JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()[0]
            current_commit = self._current_commit_from_db(db)
            buds = tuple(self._buds_from_db(db))
            branch_rows = list(
                db.execute(
                    "SELECT id, name, commit_id, comment, created_at FROM branches WHERE deleted=0 ORDER BY name"
                )
            )
            deleted_branches = tuple(self._deleted_branches_from_db(db))
            tag_rows = list(
                db.execute(
                    "SELECT name, commit_id, comment, created_at "
                    "FROM tags ORDER BY name"
                )
            )

        commits = tuple(
            GraphCommit(
                id=row["id"],
                parent_id=row["parent_id"],
                branch_id=row["branch_id"],
                branch_name=row["branch_name"],
                created_at=row["created_at"],
                message=row["message"],
                attachments=attachments[row["id"]],
                note=annotations[row["id"]].note,
                note_updated_at=annotations[row["id"]].note_updated_at,
                labels=annotations[row["id"]].labels,
            )
            for row in commit_rows
        )
        branches = tuple(
            BranchReference(
                id=row["id"],
                name=row["name"],
                commit_id=row["commit_id"],
                comment=row["comment"],
                current=row["name"] == current_branch,
                created_at=row["created_at"],
            )
            for row in branch_rows
        )
        tags = tuple(
            TagReference(
                name=row["name"],
                commit_id=row["commit_id"],
                comment=row["comment"],
                created_at=row["created_at"],
            )
            for row in tag_rows
        )
        return CommitGraph(
            commits=commits,
            branches=branches,
            tags=tags,
            current_commit=current_commit,
            buds=buds,
            deleted_branches=deleted_branches,
        )

    @staticmethod
    def _normalize_label(label: str) -> str:
        normalized = unicodedata.normalize("NFC", label.strip())
        if not normalized:
            raise SproutError("label cannot be empty", code="empty_label")
        if len(normalized) > LABEL_MAX_CHARS:
            raise SproutError(
                f"label exceeds {LABEL_MAX_CHARS} character limit",
                code="label_too_long",
                details={"limit": LABEL_MAX_CHARS},
            )
        return normalized

    @locked
    def set_message(self, value: str, message: str) -> tuple[str, str]:
        commit_id = self.resolve_commit(value)
        normalized = message.strip()
        if not normalized:
            raise SproutError("commit message cannot be empty", code="empty_message")
        with self.connect() as db:
            db.execute(
                "UPDATE commits SET message=? WHERE id=?",
                (normalized, commit_id),
            )
        return commit_id, normalized

    @locked
    def set_note(self, value: str, note: str) -> CommitAnnotations:
        commit_id = self.resolve_commit(value)
        normalized = note.strip()
        if len(normalized) > NOTE_MAX_CHARS:
            raise SproutError(f"note exceeds {NOTE_MAX_CHARS} character limit", code="note_too_long", details={"limit": NOTE_MAX_CHARS})
        with self.connect() as db:
            self._write_note(db, commit_id, normalized)
        return self.annotations(commit_id)

    @staticmethod
    def _write_note(db: sqlite3.Connection, commit_id: str, normalized: str) -> None:
        if not normalized:
            before = {"commit_notes": recovery.rows(db, "commit_notes", "commit_id=?", (commit_id,))}
            db.execute("DELETE FROM commit_notes WHERE commit_id=?", (commit_id,))
            for row in before["commit_notes"]:
                title = row["note"].splitlines()[0][:40]
                recovery.record(db, before, "note_delete", title, commit_id, utc_timestamp())
        else:
            db.execute(
                "INSERT INTO commit_notes(commit_id, note, updated_at) "
                "VALUES(?, ?, ?) ON CONFLICT(commit_id) DO UPDATE SET "
                "note=excluded.note, updated_at=excluded.updated_at",
                (commit_id, normalized, utc_timestamp()),
            )

    @locked
    def edit_leaf(
        self, value: str, *, message: str | object = UNCHANGED, note: str | object = UNCHANGED,
    ) -> tuple[str, str, CommitAnnotations]:
        """Edit the requested descriptions in one transaction, preserving omitted fields."""
        if message is UNCHANGED and note is UNCHANGED:
            raise SproutError("specify --message, --note, or --clear-note", code="no_edit_fields")
        commit_id = self.resolve_commit(value)
        if message is not UNCHANGED:
            message = message.strip()
            if not message:
                raise SproutError("commit message cannot be empty", code="empty_message")
        if note is not UNCHANGED:
            note = note.strip()
            if len(note) > NOTE_MAX_CHARS:
                raise SproutError(f"note exceeds {NOTE_MAX_CHARS} character limit", code="note_too_long", details={"limit": NOTE_MAX_CHARS})
        with self.connect() as db:
            if message is not UNCHANGED:
                db.execute("UPDATE commits SET message=? WHERE id=?", (message, commit_id))
            if note is not UNCHANGED:
                self._write_note(db, commit_id, note)
            result_message = db.execute("SELECT message FROM commits WHERE id=?", (commit_id,)).fetchone()[0]
        return commit_id, result_message, self.annotations(commit_id)

    @locked
    def add_label(self, value: str, label: str) -> CommitAnnotations:
        commit_id = self.resolve_commit(value)
        normalized = self._normalize_label(label)
        with self.connect() as db:
            exists = db.execute(
                "SELECT 1 FROM commit_labels WHERE commit_id=? AND label=?",
                (commit_id, normalized),
            ).fetchone()
            if exists is None:
                count = db.execute(
                    "SELECT COUNT(*) FROM commit_labels WHERE commit_id=?",
                    (commit_id,),
                ).fetchone()[0]
                if count >= LABEL_MAX_COUNT:
                    raise SproutError(
                        f"commit cannot have more than {LABEL_MAX_COUNT} labels",
                        code="too_many_labels",
                        details={"limit": LABEL_MAX_COUNT},
                    )
                db.execute(
                    "INSERT INTO commit_labels(commit_id, label) VALUES(?, ?)",
                    (commit_id, normalized),
                )
        return self.annotations(commit_id)

    @locked
    def remove_label(self, value: str, label: str) -> CommitAnnotations:
        commit_id = self.resolve_commit(value)
        normalized = self._normalize_label(label)
        with self.connect() as db:
            db.execute(
                "DELETE FROM commit_labels WHERE commit_id=? AND label=?",
                (commit_id, normalized),
            )
        return self.annotations(commit_id)

    def project_labels(self) -> list[dict[str, Any]]:
        """Count current label usage across live leaves, irrespective of branch reachability."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT labels.label AS name, COUNT(DISTINCT labels.commit_id) AS leaf_count "
                "FROM commit_labels AS labels JOIN commits ON commits.id=labels.commit_id "
                "GROUP BY labels.label ORDER BY labels.label COLLATE BINARY"
            ).fetchall()
        return [dict(row) for row in rows]

    def thumbnail(self, value: str) -> CommitAttachment | None:
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM commit_attachments WHERE commit_id=? AND role=?",
                (commit_id, THUMBNAIL_ROLE),
            ).fetchone()
        return self._attachment_from_row(row) if row is not None else None

    @locked
    def set_thumbnail(self, value: str, source: Path) -> CommitAttachment:
        commit_id = self.resolve_commit(value)
        original_name, media_type, object_hash, size = self._prepare_thumbnail(source)
        updated_at = utc_timestamp()
        with self.connect() as db:
            self._register_objects(db, {object_hash: size}, updated_at)
            db.execute(
                "INSERT INTO commit_attachments("
                "id, commit_id, role, original_name, media_type, object_hash, size, "
                "created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(commit_id) WHERE role='thumbnail' DO UPDATE SET "
                "original_name=excluded.original_name, "
                "media_type=excluded.media_type, "
                "object_hash=excluded.object_hash, size=excluded.size, "
                "updated_at=excluded.updated_at",
                (
                    uuid.uuid4().hex,
                    commit_id,
                    THUMBNAIL_ROLE,
                    original_name,
                    media_type,
                    object_hash,
                    size,
                    updated_at,
                    updated_at,
                ),
            )
        result = self.thumbnail(commit_id)
        if result is None:
            raise SproutError(f"failed to store thumbnail for commit: {commit_id}")
        return result

    @locked
    def delete_thumbnail(self, value: str) -> CommitAttachment:
        commit_id = self.resolve_commit(value)
        existing = self.thumbnail(commit_id)
        if existing is None:
            raise SproutError(f"commit has no thumbnail: {commit_id}", code="no_thumbnail", details={"commit_id": commit_id})
        with self.connect() as db:
            db.execute(
                "DELETE FROM commit_attachments WHERE commit_id=? AND role=?",
                (commit_id, THUMBNAIL_ROLE),
            )
        return existing

    def export_thumbnail(
        self, value: str, output: Path, *, force: bool = False
    ) -> Path:
        attachment = self.thumbnail(value)
        if attachment is None:
            raise SproutError(f"commit has no thumbnail: {self.resolve_commit(value)}", code="no_thumbnail")
        return self._export_attachment(attachment, output, force=force)

    def _export_attachment(
        self, attachment: CommitAttachment, output: Path, *, force: bool = False
    ) -> Path:
        role = attachment.role
        destination = output.resolve(strict=False)
        if destination == self.control or self.control in destination.parents:
            raise SproutError(f"cannot export {role} into Sprout metadata", code="export_into_metadata")
        if destination.exists() and not destination.is_file():
            raise SproutError(f"{role} output is not a file: {output}", code="export_path_not_file", details={"path": str(output)})
        try:
            relative = destination.relative_to(self.root).as_posix()
        except ValueError:
            relative = None
        if relative is not None and self._path_key(relative) in {
            self._path_key(path) for path in self.tracked()
        }:
            raise SproutError(f"{role} output would change tracked file: {relative}", code="export_would_change_tracked", details={"path": str(relative)})
        if destination.exists() and not force:
            raise SproutError(f"{role} output already exists: {output}", code="export_output_exists", details={"path": str(output)})

        item = FileState(
            attachment.original_name,
            attachment.object_hash,
            attachment.size,
            0,
        )
        self._copy_verified_object(item)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not force:
            try:
                with destination.open("xb") as target:
                    self._copy_verified_object(item, target)
                    target.flush()
                    os.fsync(target.fileno())
            except FileExistsError as exc:
                raise SproutError(f"{role} output already exists: {output}", code="export_output_exists", details={"path": str(output)}) from exc
            except Exception:
                destination.unlink(missing_ok=True)
                raise
            return destination

        fd, temp_name = tempfile.mkstemp(
            dir=destination.parent,
            prefix=f".{destination.name}.{role}-",
        )
        try:
            with os.fdopen(fd, "wb") as target:
                self._copy_verified_object(item, target)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temp_name, destination)
        except Exception:
            Path(temp_name).unlink(missing_ok=True)
            raise
        return destination

    @staticmethod
    def _preview_source(source: Path) -> Path:
        try:
            resolved = source.resolve(strict=True)
        except OSError as exc:
            raise SproutError(f"preview file does not exist: {source}", code="preview_file_not_found", details={"path": str(source)}) from exc
        if not resolved.is_file():
            raise SproutError(f"preview is not a file: {source}", code="preview_not_file", details={"path": str(source)})
        return resolved

    @staticmethod
    def _preview_media_type(source: Path, media_type: str | None) -> str:
        if media_type is not None:
            normalized = media_type.strip().lower()
            if not MEDIA_TYPE_PATTERN.match(normalized):
                raise SproutError(f"invalid media type: {media_type}")
            return normalized
        guessed, _ = mimetypes.guess_type(source.name, strict=False)
        return guessed or PREVIEW_DEFAULT_MEDIA_TYPE

    def plan_previews(
        self, sources: list[Path], media_type: str | None = None
    ) -> list[PreviewPlan]:
        """Report the size and storage impact of preview files without storing them."""
        if not sources:
            raise SproutError("no preview files given", code="no_preview_files")
        plans: list[PreviewPlan] = []
        with self.connect() as db:
            for source in sources:
                resolved = self._preview_source(source)
                kind = self._preview_media_type(source, media_type)
                digest = hashlib.sha256()
                size = 0
                with resolved.open("rb") as input_file:
                    for chunk in iter(lambda: input_file.read(IO_CHUNK_SIZE), b""):
                        digest.update(chunk)
                        size += len(chunk)
                object_hash = digest.hexdigest()
                already_stored = db.execute(
                    "SELECT 1 FROM objects WHERE hash=? AND size=?", (object_hash, size)
                ).fetchone() is not None
                plans.append(
                    PreviewPlan(
                        source=str(source),
                        original_name=source.name,
                        media_type=kind,
                        size=size,
                        object_hash=object_hash,
                        already_stored=already_stored,
                        additional_bytes=0 if already_stored else size,
                        requires_confirmation=size > PREVIEW_CONFIRM_BYTES,
                    )
                )
        return plans

    def _prepare_previews(
        self, sources: list[Path], media_type: str | None, confirm_large: bool
    ) -> list[tuple[str, str, str, int]]:
        """Validate every source before storing any, then store their objects."""
        if not sources:
            raise SproutError("no preview files given", code="no_preview_files")
        checked: list[tuple[Path, Path, os.stat_result, str]] = []
        for source in sources:
            resolved = self._preview_source(source)
            kind = self._preview_media_type(source, media_type)
            before = resolved.stat()
            if before.st_size > PREVIEW_CONFIRM_BYTES and not confirm_large:
                raise SproutError(
                    f"preview exceeds {PREVIEW_CONFIRM_BYTES} bytes and needs "
                    f"confirmation: {source} ({before.st_size} bytes)",
                    code="preview_confirmation_required",
                    details={
                        "source": str(source),
                        "size": before.st_size,
                        "threshold": PREVIEW_CONFIRM_BYTES,
                    },
                )
            checked.append((source, resolved, before, kind))
        prepared: list[tuple[str, str, str, int]] = []
        for source, resolved, before, kind in checked:
            object_hash, size = self._store_object(resolved)
            after = resolved.stat()
            if (
                before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
                or size != after.st_size
            ):
                raise SproutError(f"preview changed while reading: {source}", code="file_changed", details={"path": str(source)})
            prepared.append((source.name, kind, object_hash, size))
        return prepared

    @classmethod
    def _previews_from_db(
        cls, db: sqlite3.Connection, commit_id: str
    ) -> list[CommitAttachment]:
        return [
            cls._attachment_from_row(row)
            for row in db.execute(
                "SELECT * FROM commit_attachments WHERE commit_id=? AND role=? "
                "ORDER BY position, id",
                (commit_id, PREVIEW_ROLE),
            )
        ]

    def previews(self, value: str) -> list[CommitAttachment]:
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            return self._previews_from_db(db, commit_id)

    @staticmethod
    def _match_preview(
        previews: list[CommitAttachment], commit_id: str, attachment_id: str
    ) -> CommitAttachment:
        """Resolve a full preview ID or a unique prefix within one commit."""
        key = attachment_id.strip().lower()
        matches = [item for item in previews if key and item.id.startswith(key)]
        exact = [item for item in matches if item.id == key]
        if exact:
            return exact[0]
        if len(matches) == 1:
            return matches[0]
        details = {"commit_id": commit_id, "attachment_id": attachment_id}
        if matches:
            raise SproutError(
                f"ambiguous preview ID: {attachment_id}",
                code="ambiguous_preview",
                details=details,
            )
        raise SproutError(
            f"commit has no preview {attachment_id}: {commit_id}",
            code="unknown_preview",
            details=details,
        )

    def preview(self, value: str, attachment_id: str) -> CommitAttachment:
        commit_id = self.resolve_commit(value)
        return self._match_preview(self.previews(commit_id), commit_id, attachment_id)

    @staticmethod
    def _renumber_previews(
        db: sqlite3.Connection, commit_id: str, ordered_ids: list[str]
    ) -> None:
        # Move every row past the current maximum first so UNIQUE(commit_id, role,
        # position) holds at each step of the renumbering.
        offset = db.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM commit_attachments "
            "WHERE commit_id=? AND role=?",
            (commit_id, PREVIEW_ROLE),
        ).fetchone()[0]
        db.executemany(
            "UPDATE commit_attachments SET position=? WHERE id=?",
            ((offset + index, item) for index, item in enumerate(ordered_ids)),
        )
        db.executemany(
            "UPDATE commit_attachments SET position=? WHERE id=?",
            ((index, item) for index, item in enumerate(ordered_ids)),
        )

    @locked
    def set_preview_metadata(self, value: str, attachment_id: str, *,
                             display_name: str | object = UNCHANGED,
                             description: str | object = UNCHANGED) -> CommitAttachment:
        commit_id = self.resolve_commit(value)
        target = self.preview(commit_id, attachment_id)
        if display_name is not UNCHANGED:
            display_name = unicodedata.normalize('NFC', display_name).strip()
            if len(display_name)>256 or any(c in display_name for c in ('\n','\r','\x00')):
                raise SproutError('display name must be at most 256 characters without line breaks', code='invalid_preview_metadata', details={'field': 'display_name'})
        if description is not UNCHANGED:
            description = unicodedata.normalize('NFC', description)
            if len(description)>20000 or '\x00' in description:
                raise SproutError('description must be at most 20000 characters', code='invalid_preview_metadata', details={'field': 'description'})
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            updates = {'updated_at':utc_timestamp()}
            for key, value in (('display_name',display_name),('description',description)):
                if value is not UNCHANGED:
                    updates[key] = value
            db.execute('UPDATE commit_attachments SET '+','.join(f'{k}=?' for k in updates)+' WHERE id=?',
                       (*updates.values(),target.id))
        return self.preview(commit_id,target.id)

    @locked
    def add_previews(
        self,
        value: str,
        sources: list[Path],
        *,
        media_type: str | None = None,
        confirm_large: bool = False,
    ) -> list[CommitAttachment]:
        """Append previews in the given order; either all are added or none are."""
        commit_id = self.resolve_commit(value)
        prepared = self._prepare_previews(sources, media_type, confirm_large)
        now = utc_timestamp()
        added: list[str] = []
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._register_objects(db, {item[2]: item[3] for item in prepared}, now)
            position = db.execute(
                "SELECT COALESCE(MAX(position) + 1, 0) FROM commit_attachments "
                "WHERE commit_id=? AND role=?",
                (commit_id, PREVIEW_ROLE),
            ).fetchone()[0]
            for index, (original_name, kind, object_hash, size) in enumerate(prepared):
                attachment_id = uuid.uuid4().hex
                db.execute(
                    "INSERT INTO commit_attachments("
                    "id, commit_id, role, position, original_name, media_type, "
                    "object_hash, size, created_at, updated_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        attachment_id,
                        commit_id,
                        PREVIEW_ROLE,
                        position + index,
                        original_name,
                        kind,
                        object_hash,
                        size,
                        now,
                        now,
                    ),
                )
                added.append(attachment_id)
            stored = {item.id: item for item in self._previews_from_db(db, commit_id)}
        return [stored[item] for item in added]

    @locked
    def replace_preview(
        self,
        value: str,
        attachment_id: str,
        source: Path,
        *,
        media_type: str | None = None,
        confirm_large: bool = False,
    ) -> CommitAttachment:
        """Replace one preview's content, keeping its ID, position, and creation time."""
        commit_id = self.resolve_commit(value)
        target = self.preview(commit_id, attachment_id)
        ((original_name, kind, object_hash, size),) = self._prepare_previews(
            [source], media_type, confirm_large
        )
        now = utc_timestamp()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            before = recovery.capture_preview(db, commit_id)
            self._register_objects(db, {object_hash: size}, now)
            updated = db.execute(
                "UPDATE commit_attachments SET original_name=?, media_type=?, "
                "object_hash=?, size=?, updated_at=? "
                "WHERE id=? AND commit_id=? AND role=?",
                (original_name, kind, object_hash, size, now, target.id, commit_id, PREVIEW_ROLE),
            ).rowcount
            if updated != 1:
                raise SproutError(f"commit has no preview {target.id}: {commit_id}", code="unknown_preview", details={"commit_id": commit_id})
            recovery.record(db, before, 'preview_replace', target.original_name, target.id, now,
                            preview_commit=commit_id)
        return self.preview(commit_id, target.id)

    @locked
    def delete_preview(self, value: str, attachment_id: str) -> CommitAttachment:
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            before = recovery.capture_preview(db, commit_id)
            previews = self._previews_from_db(db, commit_id)
            target = self._match_preview(previews, commit_id, attachment_id)
            db.execute("DELETE FROM commit_attachments WHERE id=?", (target.id,))
            self._renumber_previews(
                db, commit_id, [item.id for item in previews if item.id != target.id]
            )
            recovery.record(db, before, 'preview_delete', target.original_name, target.id, utc_timestamp(),
                            preview_commit=commit_id)
        return target

    @locked
    def reorder_previews(
        self, value: str, attachment_ids: list[str]
    ) -> list[CommitAttachment]:
        """Save a new display order; every preview of the commit is listed once."""
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previews = self._previews_from_db(db, commit_id)
            ordered = [
                self._match_preview(previews, commit_id, item).id for item in attachment_ids
            ]
            if len(set(ordered)) != len(ordered) or len(ordered) != len(previews):
                raise SproutError(
                    "preview order must list every preview of the commit exactly once",
                    code="invalid_preview_order",
                    details={
                        "commit_id": commit_id,
                        "expected": [item.id for item in previews],
                        "given": attachment_ids,
                    },
                )
            self._renumber_previews(db, commit_id, ordered)
            return self._previews_from_db(db, commit_id)

    def export_preview(
        self, value: str, attachment_id: str, output: Path, *, force: bool = False
    ) -> Path:
        return self._export_attachment(
            self.preview(value, attachment_id), output, force=force
        )

    @staticmethod
    def _commit_path_hash(db: sqlite3.Connection, commit_id: str, path: str) -> str | None:
        row = db.execute(
            "SELECT object_hash FROM commit_files WHERE commit_id=? AND path_key=?",
            (commit_id, path_key(path)),
        ).fetchone()
        return row[0] if row else None

    def file_history(self, file_id: str) -> list[dict[str, Any]]:
        if not re.fullmatch(r"[0-9a-f]{32}", file_id):
            raise SproutError("file ID must be a complete 32-character ID", code="invalid_file_id")
        with self.connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT c.id AS commit_id,c.created_at,c.message,f.path,f.file_id,f.object_hash,f.size,f.mtime_ns "
                "FROM commit_files f JOIN commits c ON c.id=f.commit_id WHERE f.file_id=? ORDER BY c.seq DESC",
                (file_id,))]

    def log(
        self,
        path: Path | None = None,
        limit: int | None = None,
        label: str | None = None,
    ) -> list[sqlite3.Row]:
        if limit is not None and limit < 1:
            raise SproutError("log limit must be at least 1")
        relative: str | None = None
        if path is not None:
            relative = self._relative_file(path, must_exist=False)
        normalized_label = self._normalize_label(label) if label is not None else None
        current = self.head_commit()
        rows: list[sqlite3.Row] = []
        with self.connect() as db:
            while current:
                row = db.execute("SELECT * FROM commits WHERE id=?", (current,)).fetchone()
                if row is None:
                    raise SproutError(f"broken history at commit: {current}")
                matches_path = relative is None
                if relative is not None:
                    current_hash = self._commit_path_hash(db, current, relative)
                    parent_id = row["parent_id"]
                    parent_hash = (
                        self._commit_path_hash(db, parent_id, relative) if parent_id else None
                    )
                    matches_path = current_hash != parent_hash
                matches_label = normalized_label is None
                if normalized_label is not None:
                    matches_label = (
                        db.execute(
                            "SELECT 1 FROM commit_labels "
                            "WHERE commit_id=? AND label=?",
                            (current, normalized_label),
                        ).fetchone()
                        is not None
                    )
                if matches_path and matches_label:
                    rows.append(row)
                if limit is not None and len(rows) >= limit:
                    break
                current = row["parent_id"]
        return rows

    def referenced_object_hashes(self) -> set[str]:
        """Return object hashes still referenced by any commit."""
        with self.connect() as db:
            return {
                row[0]
                for row in db.execute(
                    "SELECT object_hash FROM commit_files "
                    "UNION SELECT object_hash FROM commit_attachments "
                    "UNION SELECT object_hash FROM bud_files "
                    "UNION SELECT object_hash FROM trash_objects"
                )
            }

    def doctor(self) -> DoctorResult:
        """Inspect repository integrity without changing the working tree."""
        issues: list[DoctorIssue] = []
        with self.connect() as db:
            objects = list(
                db.execute("SELECT hash, size, stored_size, encoding FROM objects ORDER BY hash")
            )
            for row in db.execute(
                "SELECT object_hash FROM commit_files "
                "UNION SELECT object_hash FROM commit_attachments "
                "UNION SELECT object_hash FROM bud_files "
                "UNION SELECT object_hash FROM trash_objects "
                "EXCEPT SELECT hash FROM objects ORDER BY 1"
            ):
                issues.append(DoctorIssue("missing_object", row[0]))
            for row in db.execute(
                "SELECT commit_id, path FROM commit_files "
                "WHERE mtime_ns IS NULL OR typeof(mtime_ns) <> 'integer' ORDER BY commit_id, path"
            ):
                issues.append(DoctorIssue("invalid_file_time", f"{row['commit_id']}:{row['path']}"))
            for item in db.execute("SELECT * FROM trash_entries"):
                try:
                    recovery.validate(db, dict(item))
                except SproutError:
                    issues.append(DoctorIssue("invalid_trash_record", item['id']))
            for table in ('tracked_paths', 'commit_files', 'bud_files'):
                for row in db.execute(f"SELECT DISTINCT f.file_id FROM {table} f "
                                      "LEFT JOIN file_identities i ON i.id=f.file_id WHERE i.id IS NULL"):
                    issues.append(DoctorIssue("missing_file_identity", row[0]))
            for table, scope in (('tracked_paths', "''"), ('commit_files', 'commit_id'), ('bud_files', 'bud_id')):
                groups: dict[str, list[str]] = {}
                for row in db.execute(f"SELECT {scope} AS scope, path, path_key FROM {table}"):
                    groups.setdefault(row["scope"], []).append(row["path"])
                    if path_key(row["path"]) != row["path_key"]:
                        issues.append(DoctorIssue("invalid_path_key", f"{table}:{row['path']}"))
                for scope_id, paths in groups.items():
                    try:
                        reject_path_conflicts(paths)
                    except SproutError as exc:
                        issues.append(DoctorIssue("path_conflict", f"{table}:{scope_id}:{exc.details['path']}"))
            cover = db.execute("SELECT value FROM meta WHERE key=?", (COVER_META_KEY,)).fetchone()
            if cover is not None and not db.execute(
                "SELECT 1 FROM file_identities WHERE id=?", (cover[0],)
            ).fetchone():
                issues.append(DoctorIssue("invalid_cover", cover[0]))
            for name in SEQUENCE_TABLES:
                counter = db.execute("SELECT last_value FROM id_sequences WHERE name=?", (name,)).fetchone()
                highest = db.execute(f"SELECT COALESCE(MAX(seq), 0) FROM {name}").fetchone()[0]
                if counter is None or counter[0] < highest:
                    issues.append(DoctorIssue("invalid_sequence", name))
            active = db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()
            if active is not None and active[0]:
                issues.append(
                    DoctorIssue("active_operation", f"interrupted operation recorded: {active[0]}")
                )
            current = self._current_commit_from_db(db)
            if current is not None and db.execute(
                "SELECT 1 FROM commits WHERE id=?", (current,)
            ).fetchone() is None:
                issues.append(DoctorIssue("missing_current_commit", current))
            for row in db.execute(
                "SELECT b.id FROM buds b LEFT JOIN commits c ON c.id = b.base_commit_id "
                "WHERE b.base_commit_id IS NOT NULL AND c.id IS NULL ORDER BY b.id"
            ):
                issues.append(DoctorIssue("missing_bud_base", row[0]))

        registered = set()
        for row in objects:
            object_hash = row["hash"]
            registered.add(object_hash)
            path = self._object_path(object_hash)
            if not path.is_file():
                issues.append(DoctorIssue("missing_object", object_hash))
                continue
            if row["encoding"] != OBJECT_COMPRESSION:
                issues.append(DoctorIssue("unsupported_object_encoding", object_hash))
                continue
            try:
                digest, size = self._read_object(path)
            except SproutError:
                digest, size = "", -1
            if digest != object_hash:
                issues.append(DoctorIssue("corrupt_object", object_hash))
            elif size != row["size"] or path.stat().st_size != row["stored_size"]:
                issues.append(DoctorIssue("object_size_mismatch", object_hash))

        if self.objects.is_dir():
            for shard in sorted(path for path in self.objects.iterdir() if path.is_dir()):
                for path in sorted(path for path in shard.iterdir() if path.is_file()):
                    if path.name not in registered:
                        issues.append(DoctorIssue("unregistered_object", path.name))

        if self.tmp.is_dir():
            for path in sorted(path for path in self.tmp.glob("object-*") if path.is_file()):
                issues.append(DoctorIssue("orphan_temp", path.name))

        return DoctorResult(
            ok=not issues,
            checked_objects=len(objects),
            issues=tuple(issues),
        )

    def stats(self) -> RepoStats:
        """Summarize repository size and basic counts without changing files."""
        with self.connect() as db:
            commits = db.execute("SELECT COUNT(*) FROM commits").fetchone()[0]
            branches = db.execute("SELECT COUNT(*) FROM branches WHERE deleted=0").fetchone()[0]
            tracked_paths = db.execute("SELECT COUNT(*) FROM tracked_paths").fetchone()[0]
            buds = db.execute("SELECT COUNT(*) FROM buds").fetchone()[0]
            logical_bytes = db.execute(
                "SELECT COALESCE(SUM(size), 0) FROM commit_files"
            ).fetchone()[0]
            unique_bytes = db.execute(
                "SELECT COALESCE(SUM(o.size), 0) FROM objects o WHERE EXISTS "
                "(SELECT 1 FROM commit_files f WHERE f.object_hash=o.hash AND f.size=o.size)"
            ).fetchone()[0]
            objects, objects_bytes = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(stored_size), 0) FROM objects"
            ).fetchone()

        return RepoStats(
            commits=commits,
            branches=branches,
            tracked_paths=tracked_paths,
            objects=objects,
            objects_bytes=objects_bytes,
            logical_bytes=logical_bytes,
            unique_bytes=unique_bytes,
            buds=buds,
        )

    @locked
    def gc(self, *, dry_run: bool = False) -> GcResult:
        """Delete unreferenced objects and leftover object temp files."""
        referenced = self.referenced_object_hashes()
        with self.connect() as db:
            unreferenced_rows = [
                row[0]
                for row in db.execute(
                    "SELECT hash FROM objects o WHERE "
                    "NOT EXISTS (SELECT 1 FROM commit_files f WHERE f.object_hash=o.hash AND f.size=o.size) "
                    "AND NOT EXISTS (SELECT 1 FROM commit_attachments a WHERE a.object_hash=o.hash AND a.size=o.size) "
                    "AND NOT EXISTS (SELECT 1 FROM bud_files b WHERE b.object_hash=o.hash AND b.size=o.size) "
                    "AND NOT EXISTS (SELECT 1 FROM trash_objects t WHERE t.object_hash=o.hash AND t.size=o.size) "
                    "ORDER BY hash"
                )
            ]
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
            # Forget rows before files: an interrupted gc leaves only unregistered
            # files, which the next gc collects.
            with self.connect() as db:
                db.executemany(
                    "DELETE FROM objects WHERE hash=?", ((object_hash,) for object_hash in unreferenced_rows)
                )
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

    @staticmethod
    def _commit_signatures_from_db(
        db: sqlite3.Connection, commit_ids: set[str]
    ) -> dict[str, dict[str, tuple[str, int, str]]]:
        signatures: dict[str, dict[str, tuple[str, int, str]]] = {
            commit_id: {} for commit_id in commit_ids
        }
        ordered = sorted(commit_ids)
        for offset in range(0, len(ordered), 900):
            chunk = ordered[offset : offset + 900]
            placeholders = ",".join("?" for _ in chunk)
            for row in db.execute(
                "SELECT commit_id, path, object_hash, size, file_id FROM commit_files "
                f"WHERE commit_id IN ({placeholders})",
                chunk,
            ):
                signatures[row["commit_id"]][row["path"]] = (
                    row["object_hash"],
                    row["size"], row["file_id"],
                )
        return signatures

    @staticmethod
    def _prune_interval(
        parents: dict[str, str | None], start_id: str, end_id: str
    ) -> set[str]:
        interval: set[str] = set()
        current: str | None = end_id
        while current is not None:
            if current in interval:
                raise SproutError("cannot prune cyclic commit history")
            interval.add(current)
            if current == start_id:
                return interval
            if current not in parents:
                raise SproutError(f"broken history at commit: {current}")
            current = parents[current]
        raise SproutError(
            "start tag must be an ancestor of end tag; specify tags from older to newer"
        )

    @staticmethod
    def _nearest_retained_parent(
        parent_id: str | None,
        parents: dict[str, str | None],
        removed: set[str],
    ) -> str | None:
        visited: set[str] = set()
        current = parent_id
        while current in removed:
            if current in visited:
                raise SproutError("cannot prune cyclic commit history")
            visited.add(current)
            if current not in parents:
                raise SproutError(f"broken history at commit: {current}")
            current = parents[current]
        return current

    def _reclaimable_objects(
        self, db: sqlite3.Connection, removed: set[str]
    ) -> tuple[tuple[str, ...], int]:
        """Objects referenced only by the removed commits, and their stored size."""
        removed_references: set[str] = set()
        retained_references: set[str] = set()
        for row in db.execute(
            "SELECT commit_id, object_hash FROM commit_files "
            "UNION ALL "
            "SELECT commit_id, object_hash FROM commit_attachments"
        ):
            target = (
                removed_references
                if row["commit_id"] in removed
                else retained_references
            )
            target.add(row["object_hash"])
        retained_references.update(row[0] for row in db.execute(
            "SELECT object_hash FROM bud_files UNION SELECT object_hash FROM trash_objects"))
        stored_sizes = {
            row["hash"]: row["stored_size"]
            for row in db.execute("SELECT hash, stored_size FROM objects")
        }
        reclaimable = tuple(
            sorted(
                object_hash
                for object_hash in removed_references - retained_references
                if object_hash in stored_sizes and self._object_path(object_hash).is_file()
            )
        )
        return reclaimable, sum(stored_sizes[object_hash] for object_hash in reclaimable)

    @locked
    def delete_commit(self, value: str, *, dry_run: bool = False) -> CommitDeletion:
        """Delete one untagged commit, moving every reference to it onto its parent.

        Branch tips, the current position and bud bases move to the parent and
        children are reconnected to it. Working files are never touched, so a
        deleted current snapshot remains as unsaved changes.
        """
        commit_id = self.resolve_commit(value)
        try:
            with self.connect() as db:
                db.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT id, parent_id, created_at, message FROM commits WHERE id=?",
                    (commit_id,),
                ).fetchone()
                if row is None:
                    raise SproutError(f"unknown commit: {commit_id}", code="unknown_commit", details={"commit_id": commit_id})
                tags = [
                    tag[0]
                    for tag in db.execute(
                        "SELECT name FROM tags WHERE commit_id=? ORDER BY name", (commit_id,)
                    )
                ]
                if tags:
                    raise SproutError(
                        f"commit {commit_id[:12]} is tagged ({', '.join(tags)}); "
                        "delete its tags first",
                        code="tagged_commit",
                        details={"commit_id": commit_id, "tags": tags},
                    )
                parent_id = row["parent_id"]
                current_branch = db.execute(
                    "SELECT head_branch_id FROM repository_state WHERE id=1"
                ).fetchone()[0]
                moved_branches = tuple(
                    BranchReference(
                        id=branch["id"],
                        name=branch["name"],
                        commit_id=parent_id,
                        comment=branch["comment"],
                        current=branch["id"] == current_branch,
                    )
                    for branch in db.execute(
                        "SELECT id, name, comment FROM branches "
                        "WHERE commit_id=? AND deleted=0 ORDER BY name",
                        (commit_id,),
                    )
                )
                moved_current = self._current_commit_from_db(db) == commit_id
                children = tuple(
                    child[0]
                    for child in db.execute(
                        "SELECT id FROM commits WHERE parent_id=? ORDER BY seq", (commit_id,)
                    )
                )
                buds = tuple(
                    bud[0]
                    for bud in db.execute(
                        "SELECT id FROM buds WHERE base_commit_id=? ORDER BY seq", (commit_id,)
                    )
                )
                reclaimable, reclaimable_bytes = self._reclaimable_objects(db, {commit_id})

                if not dry_run:
                    before = recovery.capture_commit(db, commit_id)
                    # Deleted branches keep their identity rows; they follow too.
                    db.execute(
                        "UPDATE branches SET commit_id=? WHERE commit_id=?", (parent_id, commit_id)
                    )
                    if moved_current:
                        self._set_current_commit(db, parent_id)
                    db.execute(
                        "UPDATE buds SET base_commit_id=? WHERE base_commit_id=?",
                        (parent_id, commit_id),
                    )
                    db.execute(
                        "UPDATE commits SET parent_id=? WHERE parent_id=?", (parent_id, commit_id)
                    )
                    db.execute("DELETE FROM commits WHERE id=?", (commit_id,))
                    recovery.record(db, before, 'commit', row['message'], commit_id, utc_timestamp())

            return CommitDeletion(
                commit=PruneCommit(row["id"], row["created_at"], row["message"]),
                dry_run=dry_run,
                parent_id=parent_id,
                moved_branches=moved_branches,
                moved_current=moved_current,
                reconnected_children=children,
                rebased_buds=buds,
                reclaimable_objects=reclaimable,
                reclaimable_bytes=reclaimable_bytes,
            )
        except sqlite3.Error as exc:
            raise SproutError(
                f"delete-commit failed; repository unchanged: {exc}",
                code="delete_commit_failed",
                details={"reason": str(exc)},
            ) from exc

    def trash_items(self, item_id: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as db:
            entries = ([recovery.load(db, item_id)] if item_id is not None else
                       [dict(row) for row in db.execute("SELECT * FROM trash_entries ORDER BY seq DESC")])
            result = []
            for entry in entries:
                protected = list(db.execute(
                    "SELECT o.hash,o.stored_size FROM objects o JOIN trash_objects t "
                    "ON t.object_hash=o.hash WHERE t.trash_id=?", (entry['id'],)))
                reclaimable = []
                for obj in protected:
                    digest = obj['hash']
                    if not db.execute(
                        "SELECT 1 FROM commit_files WHERE object_hash=? UNION ALL "
                        "SELECT 1 FROM commit_attachments WHERE object_hash=? UNION ALL "
                        "SELECT 1 FROM bud_files WHERE object_hash=? UNION ALL "
                        "SELECT 1 FROM trash_objects WHERE object_hash=? AND trash_id<>? LIMIT 1",
                        (digest, digest, digest, digest, entry['id'])).fetchone():
                        reclaimable.append(obj)
                result.append({k: entry[k] for k in ('id','kind','target_id','title','created_at')} | {
                    'protected_bytes': sum(o['stored_size'] for o in protected),
                    'reclaimable_bytes': sum(o['stored_size'] for o in reclaimable),
                    'objects': [o['hash'] for o in protected],
                })
            return result

    def trash_detail(self, item_id: str) -> dict[str, Any]:
        result = self.trash_items(item_id)[0]
        with self.connect() as db:
            payload = recovery.validate(db, recovery.load(db, item_id))
        # Recovery stores complete V1 rows, but retired storage markers are not
        # part of the public attachment metadata or recovery presentation.
        changes = [{key: ({k: v for k, v in value.items() if k != 'is_primary'}
                          if patch['table'] == 'commit_attachments' and isinstance(value, dict)
                          else value) for key, value in patch.items()}
                   for patch in payload['patches'] if patch['table'] != 'preview_assets']
        return result | {'changes': changes}

    @locked
    def restore_trash(self, item_id: str, *, dry_run: bool = False) -> dict[str, Any]:
        result = self.trash_detail(item_id)
        try:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                item = recovery.load(db, item_id)
                # Verify original content before committing metadata that refers to it.
                for obj in db.execute("SELECT object_hash,size FROM trash_objects WHERE trash_id=?", (item_id,)):
                    self._copy_verified_object(FileState('', obj['object_hash'], obj['size'], 0))
                recovery.restore(db, item)
                if db.execute("PRAGMA foreign_key_check").fetchone():
                    recovery.conflict(item_id, 'a required reference is missing', 'missing_reference')
                if dry_run:
                    db.rollback()
            return result | {'restored': not dry_run, 'dry_run': dry_run}
        except sqlite3.Error as exc:
            recovery.conflict(item_id, 'a restored record conflicts with an existing name, position or reference', 'record_conflict')

    @locked
    def purge_trash(self, item_id: str, *, dry_run: bool = False) -> dict[str, Any]:
        result = self.trash_items(item_id)[0]
        if not dry_run:
            with self.connect() as db:
                db.execute("DELETE FROM trash_entries WHERE id=?", (item_id,))
        return result | {'purged': not dry_run, 'dry_run': dry_run}

    @locked
    def prune(
        self,
        start_tag: str | None = None,
        end_tag: str | None = None,
        *,
        all_history: bool = False,
        dry_run: bool = False,
    ) -> PruneResult:
        """Remove unprotected commits while preserving references and ancestry."""
        if all_history:
            if start_tag is not None or end_tag is not None:
                raise SproutError("--all cannot be combined with tag arguments")
        elif start_tag is None or end_tag is None:
            raise SproutError("specify START_TAG END_TAG or --all")

        try:
            with self.connect() as db:
                db.execute("BEGIN" if dry_run else "BEGIN IMMEDIATE")
                commit_rows = list(
                    db.execute(
                        "SELECT id, parent_id, created_at, message FROM commits "
                        "ORDER BY seq"
                    )
                )
                parents = {row["id"]: row["parent_id"] for row in commit_rows}
                tag_rows = list(db.execute("SELECT name, commit_id FROM tags"))
                tags = {row["name"]: row["commit_id"] for row in tag_rows}
                branch_tips = {
                    row[0]
                    for row in db.execute(
                        "SELECT commit_id FROM branches WHERE deleted=0 AND commit_id IS NOT NULL"
                    )
                }
                protected = set(tags.values()) | branch_tips
                current = self._current_commit_from_db(db)
                if current is not None:
                    protected.add(current)
                protected |= {
                    row[0]
                    for row in db.execute(
                        "SELECT base_commit_id FROM buds WHERE base_commit_id IS NOT NULL"
                    )
                }

                if all_history:
                    candidates = set(parents) - protected
                    mode = "all"
                else:
                    assert start_tag is not None and end_tag is not None
                    if start_tag not in tags:
                        raise SproutError(f"unknown tag: {start_tag}")
                    if end_tag not in tags:
                        raise SproutError(f"unknown tag: {end_tag}")
                    interval = self._prune_interval(
                        parents, tags[start_tag], tags[end_tag]
                    )
                    candidates = interval - protected
                    mode = "between"

                retained = set(parents) - candidates
                parent_updates = [
                    (
                        self._nearest_retained_parent(
                            parents[commit_id], parents, candidates
                        ),
                        commit_id,
                    )
                    for commit_id in sorted(retained)
                    if parents[commit_id] in candidates
                ]

                reclaimable, reclaimable_bytes = self._reclaimable_objects(db, candidates)
                removed_commits = tuple(
                    PruneCommit(row["id"], row["created_at"], row["message"])
                    for row in commit_rows
                    if row["id"] in candidates
                )

                if not dry_run and candidates:
                    tracked = {
                        row[0] for row in db.execute("SELECT path FROM tracked_paths")
                    }
                    working_signature: dict[str, tuple[str, int, str]] | None = None
                    if all((self.root / Path(relative)).is_file() for relative in tracked):
                        bindings = self.tracked_ids()
                        working_signature = {p: (*value, bindings[p]) for p, value in self._hash_worktree_files(tracked).items()}
                    if working_signature is not None:
                        current_tip = db.execute(
                            "SELECT b.commit_id FROM branches b "
                            "JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
                        ).fetchone()
                        head_id = current_tip[0] if current_tip is not None else None
                        compared = set(candidates)
                        if head_id is not None:
                            compared.add(head_id)
                        signatures = self._commit_signatures_from_db(db, compared)
                        head_signature = signatures.get(head_id, {})
                        if working_signature != head_signature:
                            matched = next(
                                (
                                    commit_id
                                    for commit_id in sorted(candidates)
                                    if signatures[commit_id] == working_signature
                                ),
                                None,
                            )
                            if matched is not None:
                                raise SproutError(
                                    "working tree matches commit "
                                    f"{matched[:12]}, which would be pruned; "
                                    "tag that commit or create a branch from it first",
                                    code="working_snapshot_would_be_pruned",
                                    details={"commit_id": matched},
                                )

                    db.executemany(
                        "UPDATE commits SET parent_id=? WHERE id=?", parent_updates
                    )
                    ordered = sorted(candidates)
                    for offset in range(0, len(ordered), 900):
                        chunk = ordered[offset : offset + 900]
                        placeholders = ",".join("?" for _ in chunk)
                        db.execute(
                            f"UPDATE commits SET parent_id=NULL "
                            f"WHERE id IN ({placeholders})",
                            chunk,
                        )
                    for offset in range(0, len(ordered), 900):
                        chunk = ordered[offset : offset + 900]
                        placeholders = ",".join("?" for _ in chunk)
                        db.execute(
                            f"DELETE FROM commits WHERE id IN ({placeholders})",
                            chunk,
                        )

            return PruneResult(
                mode=mode,
                dry_run=dry_run,
                start_tag=start_tag,
                end_tag=end_tag,
                commits=removed_commits,
                reclaimable_objects=reclaimable,
                reclaimable_bytes=reclaimable_bytes,
            )
        except sqlite3.Error as exc:
            raise SproutError(
                f"prune failed; repository unchanged: {exc}",
                code="prune_failed",
            ) from exc

    def branch_references(self) -> list[BranchReference]:
        """Read names, identities and current selection from one SQLite snapshot."""
        with self.connect() as db:
            return [
                BranchReference(
                    id=row["id"], name=row["name"], commit_id=row["commit_id"],
                    comment=row["comment"], current=bool(row["current"]), created_at=row["created_at"],
                )
                for row in db.execute(
                    "SELECT b.id, b.name, b.commit_id, b.comment, b.created_at, "
                    "b.id=s.head_branch_id AS current FROM branches b "
                    "CROSS JOIN repository_state s WHERE s.id=1 AND b.deleted=0 ORDER BY b.name"
                )
            ]

    @staticmethod
    def _deleted_branches_from_db(db: sqlite3.Connection) -> list[DeletedBranch]:
        return [
            DeletedBranch(row["id"], row["name"], row["comment"], row["created_at"], row["deleted_at"])
            for row in db.execute(
                "SELECT id, name, comment, created_at, deleted_at FROM branches "
                "WHERE deleted=1 ORDER BY deleted_at DESC, id"
            )
        ]

    def deleted_branches(self) -> list[DeletedBranch]:
        with self.connect() as db:
            return self._deleted_branches_from_db(db)

    def branches(self) -> list[tuple[str, str | None, str]]:
        return [(branch.name, branch.commit_id, branch.comment) for branch in self.branch_references()]

    def tags(self) -> list[tuple[str, str, str, str]]:
        with self.connect() as db:
            return [
                (row[0], row[1], row[2], row[3])
                for row in db.execute(
                    "SELECT name, commit_id, comment, created_at FROM tags ORDER BY name"
                )
            ]

    @staticmethod
    def _validate_reference_name(name: str, kind: str) -> None:
        if not name or any(c.isspace() for c in name) or name.startswith("-"):
            raise SproutError(f"{kind} name must be non-empty and contain no whitespace", code="invalid_reference_name", details={"kind": kind})
        if HEX_BRANCH_NAME.fullmatch(name):
            raise SproutError(f"{kind} name cannot look like a commit id prefix", code="reference_name_like_commit_id", details={"kind": kind})

    def _matching_saved_snapshot_commit(
        self, signature: dict[str, tuple[str, int]]
    ) -> str | None:
        """Return a commit id whose manifest exactly matches signature, if any."""
        with self.connect() as db:
            if not signature:
                row = db.execute(
                    "SELECT c.id FROM commits c WHERE NOT EXISTS "
                    "(SELECT 1 FROM commit_files f WHERE f.commit_id = c.id) "
                    "ORDER BY c.seq LIMIT 1"
                ).fetchone()
                return row[0] if row is not None else None
            # Every candidate already contains all signature files, so an equal
            # file count means the manifests are identical.
            for commit_id in sorted(self._commits_containing_from_db(db, signature)):
                count = db.execute(
                    "SELECT COUNT(*) FROM commit_files WHERE commit_id=?", (commit_id,)
                ).fetchone()[0]
                if count == len(signature) and self._snapshot_ids_match(db, commit_id, signature):
                    return commit_id
        return None

    @staticmethod
    def _commits_containing_from_db(
        db: sqlite3.Connection, signature: dict[str, tuple[str, int]]
    ) -> set[str]:
        """Return commits that contain every file in signature, using the object index."""
        matching: set[str] | None = None
        for path, (object_hash, size) in sorted(signature.items()):
            rows = {row[0] for row in db.execute(SAVED_FILE_COMMITS_SQL, (object_hash, size, path))}
            matching = rows if matching is None else matching & rows
            if not matching:
                return set()
        return matching or set()

    def _reject_omitted_start_point_on_restored_snapshot(self, head: str) -> None:
        """Refuse tip-based branching when a different saved snapshot is checked out."""
        current = self.current_commit()
        if current == head:
            return
        if current is None:
            raise SproutError(
                "working tree is based on the state before the first commit; specify the start point explicitly"
            )
        raise SproutError(
            "working tree is based on a saved snapshot that differs from the current "
            "branch tip; specify the start point explicitly "
            f"(example: sprout branch NAME {current[:12]})"
        )

    @locked
    def create_branch(
        self,
        name: str,
        comment: str = "",
        *,
        start_point: str | None = None,
        switch: bool = False,
    ) -> str:
        self._validate_reference_name(name, "branch")
        if switch:
            self._validate_restore_inputs({})
        if start_point is not None:
            commit_id = self.resolve_commit(start_point)
        else:
            head = self.head_commit()
            if head is None:
                raise SproutError("cannot create branch before first commit")
            self._reject_omitted_start_point_on_restored_snapshot(head)
            commit_id = head
        if switch:
            self._validate_restore_inputs(self.manifest(commit_id))
        if switch and self._has_unsaved_changes():
            raise SproutError(
                "working tree has uncommitted changes; commit them first, or discard "
                "tracked changes with switch/restore --discard before creating and switching",
                code="uncommitted_changes",
                details={"can_discard": True},
            )
        self._insert_branch(name, commit_id, comment)
        if switch:
            try:
                self._materialize(
                    self.manifest(commit_id), head_branch=name, current_commit=commit_id
                )
            except Exception:
                self._forget_unused_branch(name)
                raise
        return commit_id

    def _insert_branch(self, name: str, commit_id: str, comment: str) -> None:
        try:
            with self.connect() as db:
                if db.execute("SELECT 1 FROM tags WHERE name=?", (name,)).fetchone() is not None:
                    raise SproutError(f"name already used by tag: {name}", code="name_used_by_tag", details={"name": name})
                db.execute(
                    "INSERT INTO branches(id, name, commit_id, comment, created_at) VALUES(?,?,?,?,?)",
                    (uuid.uuid4().hex, name, commit_id, comment.strip(), utc_timestamp()),
                )
        except sqlite3.IntegrityError as exc:
            raise SproutError(f"branch already exists: {name}", code="branch_exists", details={"name": name}) from exc

    def _forget_unused_branch(self, name: str) -> None:
        with self.connect() as db:
            db.execute(
                "DELETE FROM branches WHERE name=? AND deleted=0 "
                "AND id != (SELECT head_branch_id FROM repository_state WHERE id=1)",
                (name,),
            )

    @locked
    def grow_branch(
        self, name: str, comment: str = "", *, start_point: str | None = None
    ) -> tuple[str, Bud | None]:
        """Create a branch and move to it, keeping unsaved changes as a bud.

        The name is checked before anything moves, so a refused branch changes nothing.
        """
        self._validate_reference_name(name, "branch")
        commit_id = self.resolve_commit(start_point) if start_point is not None else self.current_commit()
        if commit_id is None:
            raise SproutError("cannot create branch before first commit")
        target = self.manifest(commit_id)
        self._validate_restore_inputs(target)
        self._insert_branch(name, commit_id, comment)
        try:
            stashed = self._materialize_keeping_changes(target, head_branch=name, current_commit=commit_id)
        except Exception:
            self._forget_unused_branch(name)
            raise
        return commit_id, stashed

    @locked
    def delete_branch(self, name: str) -> str:
        """Delete a live branch and return its identity."""
        with self.connect() as db:
            branch = db.execute("SELECT id FROM branches WHERE name=? AND deleted=0", (name,)).fetchone()
            if branch is None:
                raise SproutError(f"unknown branch: {name}", code="unknown_branch", details={"name": name})
            current = db.execute(
                "SELECT b.name FROM branches b JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()[0]
            if name == current:
                raise SproutError(f"cannot delete current branch: {name}", code="current_branch_delete", details={"name": name})
            before = {"branches": recovery.rows(db, "branches", "id=?", (branch[0],))}
            deleted_at = utc_timestamp()
            db.execute(
                "UPDATE branches SET deleted=1, commit_id=NULL, deleted_at=? WHERE id=?",
                (deleted_at, branch[0]),
            )
            recovery.record(db, before, "branch_delete", name, branch[0], deleted_at)
        return branch[0]

    @locked
    def rename_branch(self, old_name: str, new_name: str) -> str:
        """Rename a live branch and return its identity."""
        self._validate_reference_name(new_name, "branch")
        with self.connect() as db:
            branch = db.execute("SELECT id FROM branches WHERE name=? AND deleted=0", (old_name,)).fetchone()
            if branch is None:
                raise SproutError(f"unknown branch: {old_name}", code="unknown_branch", details={"name": old_name})
            duplicate = db.execute(
                "SELECT 1 FROM branches WHERE name=? AND deleted=0", (new_name,)
            ).fetchone()
            if duplicate is not None:
                raise SproutError(f"branch already exists: {new_name}", code="branch_exists", details={"name": new_name})
            if (
                db.execute("SELECT 1 FROM tags WHERE name=?", (new_name,)).fetchone()
                is not None
            ):
                raise SproutError(f"name already used by tag: {new_name}", code="name_used_by_tag", details={"name": new_name})
            db.execute("UPDATE branches SET name=? WHERE id=?", (new_name, branch[0]))
        return branch[0]

    @locked
    def create_tag(
        self, name: str, commit: str | None = None, comment: str = ""
    ) -> str:
        self._validate_reference_name(name, "tag")
        commit_id = self.resolve_commit(commit) if commit is not None else self.head_commit()
        if commit_id is None:
            raise SproutError("cannot create tag before first commit")
        created_at = utc_timestamp()
        try:
            with self.connect() as db:
                if (
                    db.execute("SELECT 1 FROM branches WHERE name=? AND deleted=0", (name,)).fetchone()
                    is not None
                ):
                    raise SproutError(f"name already used by branch: {name}", code="name_used_by_branch", details={"name": name})
                db.execute(
                    "INSERT INTO tags(name, commit_id, comment, created_at) VALUES(?,?,?,?)",
                    (name, commit_id, comment.strip(), created_at),
                )
        except sqlite3.IntegrityError as exc:
            raise SproutError(f"tag already exists: {name}", code="tag_exists", details={"name": name}) from exc
        return commit_id

    @locked
    def delete_tag(self, name: str) -> None:
        with self.connect() as db:
            before = {"tags": recovery.rows(db, "tags", "name=?", (name,))}
            if not before["tags"]:
                raise SproutError(f"unknown tag: {name}", code="unknown_tag", details={"name": name})
            db.execute("DELETE FROM tags WHERE name=?", (name,))
            recovery.record(db, before, "tag_delete", name, before["tags"][0]["commit_id"], utc_timestamp())

    @locked
    def set_tag_comment(self, name: str, comment: str) -> None:
        with self.connect() as db:
            cursor = db.execute("UPDATE tags SET comment=? WHERE name=?", (comment.strip(), name))
            if cursor.rowcount == 0:
                raise SproutError(f"unknown tag: {name}", code="unknown_tag", details={"name": name})

    @locked
    def set_branch_comment(self, name: str, comment: str) -> str:
        """Replace a live branch comment and return the branch identity."""
        with self.connect() as db:
            branch_id = self._branch_id_from_db(db, name)
            db.execute("UPDATE branches SET comment=? WHERE id=?", (comment.strip(), branch_id))
        return branch_id

    def _verify_manifest(self, target: dict[str, FileState]) -> None:
        for item in target.values():
            self._copy_verified_object(item)

    def _safe_restore_path(self, relative: str, *, internal: bool = False) -> Path:
        """Inspect every component without following links, including dangling links."""
        path = Path(relative)
        def reject(reason: str) -> None:
            raise SproutError(
                f"unsafe restore path: {relative} ({reason})",
                code="unsafe_restore_path",
                details={"path": relative, "reason": reason},
            )
        if (not relative or "\x00" in relative or path.anchor or ".." in path.parts
                or not path.parts or any(":" in part for part in path.parts)):
            reject("path must be relative and inside the repository")
        if os.name == "nt" and any(part.rstrip(" .") != part for part in path.parts):
            reject("ambiguous Windows path component")
        metadata = self._path_key(path.parts[0]) == self._path_key(CONTROL_DIR)
        if metadata != internal:
            reject("invalid metadata boundary")
        current = self.root
        for part in path.parts:
            current = current / part
            try:
                info = current.lstat()
            except (FileNotFoundError, NotADirectoryError):
                continue  # A tracked file may be replaced by a directory later.
            if stat.S_ISLNK(info.st_mode) or (
                getattr(info, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                reject("symbolic links and reparse points are not supported")
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                reject("not a regular file or directory")
        return self.root / path

    def _restore_internal(self, path: Path) -> Path:
        return self._safe_restore_path(path.relative_to(self.root).as_posix(), internal=True)

    def _restore_tree_files(self, directory: Path) -> list[Path]:
        """Validate a private operation tree before reading or removing it."""
        self._restore_internal(directory)
        files: list[Path] = []
        if directory.exists():
            for base, dirs, names in os.walk(directory, followlinks=False):
                for name in dirs + names:
                    child = self._restore_internal(Path(base) / name)
                    if child.is_file():
                        files.append(child)
        return files

    def _validate_restore_inputs(self, target: dict[str, FileState], *, partial: bool = False) -> None:
        self._adopt_disk_spellings()
        ids = [item.file_id for item in target.values()]
        if len(set(ids)) != len(ids):
            raise SproutError("duplicate file identity in snapshot", code="file_identity_conflict")
        reject_path_conflicts(target)
        if partial:
            bindings = {path_key(path): identity for path, identity in self.tracked_ids().items()}
            target_keys = {path_key(path) for path in target}
            for path, item in target.items():
                key = path_key(path)
                if (key in bindings and bindings[key] != item.file_id) or any(
                    p not in target_keys and identity == item.file_id for p, identity in bindings.items()
                ):
                    raise SproutError(f"partial restore file identity collision: {path}",
                                      code="file_identity_conflict", details={"path": path, "file_id": item.file_id})
        paths = set(target) if partial else set(target) | self.tracked() | set(self.manifest(self.current_commit()))
        for relative in paths:
            self._safe_restore_path(relative)
        self._restore_internal(self.tmp)

    def _restore_plan(self, target: dict[str, FileState], *, partial: bool) -> dict[str, Any]:
        self._validate_restore_inputs(target, partial=partial)
        tracked = self.tracked()
        tracked_by_key = {self._path_key(p): p for p in tracked}
        selected = {self._path_key(p) for p in target}
        changed = selected if partial else set(tracked_by_key) | selected
        originals: dict[str, Path] = {}
        remove_dirs: set[str] = set()
        create_dirs: set[str] = set()

        def conflict(relative: str) -> None:
            if partial and self._path_key(relative) in tracked_by_key:
                raise SproutError(
                    f"partial restore would change unselected path: {relative}; use a full restore",
                    code="restore_scope_conflict",
                    details={"path": relative, "reason": "unselected tracked path blocks restoration"},
                )
            raise SproutError(
                f"untracked path would be overwritten: {relative}",
                code="untracked_conflict",
                details={"path": relative, "reason": "untracked path would be overwritten"},
            )

        def removable_directory(relative: str) -> None:
            directory = self._safe_restore_path(relative)
            children = list(directory.iterdir())
            if not children:
                conflict(relative)
            for child in children:
                name = child.relative_to(self.root).as_posix()
                self._safe_restore_path(name)
                if child.is_dir():
                    removable_directory(name)
                elif self._path_key(name) not in changed or self._path_key(name) not in tracked_by_key:
                    conflict(name)
            remove_dirs.add(relative)

        for relative in sorted(tracked):
            if self._path_key(relative) in changed:
                path = self._safe_restore_path(relative)
                if path.is_file():
                    originals[relative] = path
        for relative in target:
            path = self._safe_restore_path(relative)
            if path.is_dir():
                removable_directory(relative)
            elif path.exists() and self._path_key(relative) not in tracked_by_key:
                conflict(relative)
            for parent in Path(relative).parents:
                if parent == Path("."):
                    continue
                name = parent.as_posix()
                directory = self._safe_restore_path(name)
                if directory.is_file():
                    if self._path_key(name) not in tracked_by_key or self._path_key(name) not in changed:
                        conflict(name)
                    create_dirs.add(name)
                elif not directory.exists():
                    create_dirs.add(name)
        # A valid snapshot cannot contain both a file and its descendant.
        for relative in target:
            if any(self._path_key(p.as_posix()) in selected for p in Path(relative).parents):
                raise SproutError(f"conflicting paths in snapshot: {relative}")
        actions: list[dict[str, Any]] = []
        hashes = self._hash_worktree_files(originals, progress=False)
        for relative, path in sorted(originals.items()):
            digest, size = hashes[relative]
            actions.append({"kind": "backup", "path": relative, "hash": digest,
                            "size": size, "mtime_ns": path.stat().st_mtime_ns})
        actions.extend({"kind": "rmdir", "path": p} for p in sorted(remove_dirs, key=lambda p: (-len(Path(p).parts), p)))
        actions.extend({"kind": "mkdir", "path": p} for p in sorted(create_dirs, key=lambda p: (len(Path(p).parts), p)))
        actions.extend({"kind": "install", "path": p, "hash": item.object_hash,
                        "size": item.size, "mtime_ns": item.mtime_ns} for p, item in sorted(target.items()))
        return {"version": RESTORE_PLAN_VERSION, "actions": actions, "attempted": 0, "rollback": None}

    def _set_active_operation(self, operation_id: str) -> None:
        with self.connect() as db:
            db.execute("UPDATE meta SET value=? WHERE key='active_operation'", (operation_id,))

    def _rollback_materialization(self, operation_dir: Path, plan: dict[str, Any]) -> None:
        self._restore_tree_files(operation_dir)
        self._validate_restore_plan(plan)
        if plan["rollback"] is None:
            plan["rollback"] = plan["attempted"] - 1
            self._write_restore_progress(operation_dir, plan)
        while plan["rollback"] >= 0:
            action = plan["actions"][plan["rollback"]]
            self._undo_restore_action(operation_dir, action)
            plan["rollback"] -= 1
            self._write_restore_progress(operation_dir, plan)

    def _validate_restore_plan(self, plan: dict[str, Any]) -> None:
        if type(plan.get("version")) is not int or plan["version"] != RESTORE_PLAN_VERSION:
            raise SproutError(
                "invalid restore recovery plan: unsupported version; backups retained",
                code="unsupported_restore_plan_version",
                details={"found_version": plan.get("version"),
                         "supported_version": RESTORE_PLAN_VERSION},
            )
        if not isinstance(plan.get("actions"), list):
            raise SproutError("invalid restore recovery plan")
        count = len(plan["actions"])
        if (type(plan.get("attempted")) is not int or not 0 <= plan["attempted"] <= count
                or (plan.get("rollback") is not None and (
                    type(plan["rollback"]) is not int or not -1 <= plan["rollback"] < plan["attempted"]))):
            raise SproutError("invalid restore recovery progress")
        for action in plan["actions"]:
            if not isinstance(action, dict) or action.get("kind") not in {"backup", "install", "mkdir", "rmdir"}:
                raise SproutError("invalid restore recovery action")
            if not isinstance(action.get("path"), str):
                raise SproutError("invalid restore recovery path")
            self._safe_restore_path(action["path"])
            if action["kind"] in {"backup", "install"} and (
                not isinstance(action.get("hash"), str) or not re.fullmatch(r"[0-9a-f]{64}", action["hash"])
                or type(action.get("size")) is not int or action["size"] < 0
                or type(action.get("mtime_ns")) is not int
            ):
                raise SproutError("invalid restore recovery file metadata")

    @staticmethod
    def _restore_conflict(relative: str) -> None:
        raise SproutError(
            f"restore recovery conflict: {relative}; backups retained; resolve the conflict and rerun Sprout",
            code="restore_recovery_conflict",
            details={"path": relative, "reason": "path changed during restoration or recovery"},
        )

    def _matches_restore_file(self, path: Path, action: dict[str, Any]) -> bool:
        return path.is_file() and self.hash_file(path) == (action["hash"], action["size"])

    def _undo_restore_action(self, operation_dir: Path, action: dict[str, Any]) -> None:
        relative = action["path"]
        destination = self._safe_restore_path(relative)
        kind = action["kind"]
        if kind == "install":
            staged = self._restore_internal(operation_dir / "staged" / relative)
            if not staged.exists():
                if not self._matches_restore_file(destination, action):
                    self._restore_conflict(relative)
                staged.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination, staged)
        elif kind == "mkdir":
            if destination.exists():
                if not destination.is_dir() or any(destination.iterdir()):
                    self._restore_conflict(relative)
                destination.rmdir()
        elif kind == "rmdir":
            if destination.exists() and not destination.is_dir():
                self._restore_conflict(relative)
            destination.mkdir(exist_ok=True)
        else:
            saved = self._restore_internal(operation_dir / "backup" / relative)
            if not saved.exists():  # The forward move was never performed.
                if not self._matches_restore_file(destination, action):
                    self._restore_conflict(relative)
                return
            if not self._matches_restore_file(saved, action):
                self._restore_conflict(relative)
            if destination.exists():
                if not self._matches_restore_file(destination, action):
                    self._restore_conflict(relative)
                if destination.stat().st_mtime_ns != action["mtime_ns"]:
                    os.utime(destination, ns=(action["mtime_ns"], action["mtime_ns"]))
                return  # Atomic replacement completed before the last checkpoint.
            temporary = self._restore_internal(operation_dir / "rollback-copy")
            with saved.open("rb") as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output, IO_CHUNK_SIZE)
                output.flush()
                os.fsync(output.fileno())
            os.utime(temporary, ns=(action["mtime_ns"], action["mtime_ns"]))
            destination.parent.mkdir(parents=True, exist_ok=True)
            self._safe_restore_path(relative)
            os.replace(temporary, destination)

    def _apply_restore_action(self, operation_dir: Path, action: dict[str, Any]) -> None:
        relative = action["path"]
        destination = self._safe_restore_path(relative)
        kind = action["kind"]
        if kind == "backup":
            if not self._matches_restore_file(destination, action):
                self._restore_conflict(relative)
            saved = self._restore_internal(operation_dir / "backup" / relative)
            saved.parent.mkdir(parents=True, exist_ok=True)
            os.replace(destination, saved)
        elif kind == "rmdir":
            destination.rmdir()
        elif kind == "mkdir":
            destination.mkdir()
        else:
            if destination.exists():
                self._restore_conflict(relative)
            source = self._restore_internal(operation_dir / "staged" / relative)
            os.replace(source, destination)
            os.utime(destination, ns=(action["mtime_ns"], action["mtime_ns"]))

    def _validate_pending_recovery(self, active: str) -> None:
        if not active.startswith("restore-") or Path(active).name != active:
            raise SproutError("invalid active restore operation")
        operation_dir = self._restore_internal(self.tmp / active)
        try:
            plan = self._read_restore_plan(operation_dir)
            self._validate_restore_plan(plan)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SproutError(f"cannot recover interrupted operation: {active}") from exc

    def _recover_pending_materialization(self) -> None:
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key='active_operation'").fetchone()
        if row is None:
            raise SproutError("repository is missing operation metadata")
        active = row[0]
        self._restore_internal(self.tmp)
        operation_dirs = list(self.tmp.glob("restore-*"))
        if active:
            if not active.startswith("restore-") or Path(active).name != active:
                raise SproutError("invalid active restore operation")
            operation_dir = self.tmp / active
            plan_path = self._restore_internal(operation_dir / "plan.json")
            if not plan_path.is_file():
                raise SproutError(f"cannot recover interrupted operation: {active}")
            try:
                plan = self._read_restore_plan(operation_dir)
                if not isinstance(plan, dict):
                    raise ValueError("plan must be an object")
                self._rollback_materialization(operation_dir, plan)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise SproutError(f"cannot recover interrupted operation: {active}") from exc
            self._set_active_operation("")
        for operation_dir in operation_dirs:
            self._restore_tree_files(operation_dir)
            shutil.rmtree(operation_dir, ignore_errors=True)

    def _write_operation_plan(self, path: Path, plan: dict[str, Any]) -> None:
        self._restore_internal(path)
        temporary = self._restore_internal(path.with_suffix(".pending"))
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(plan, file, ensure_ascii=False, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)

    def _write_restore_progress(self, operation_dir: Path, plan: dict[str, Any]) -> None:
        # Keep checkpoints constant-sized even for snapshots with many files.
        self._write_operation_plan(operation_dir / "progress.json", {
            "attempted": plan["attempted"], "rollback": plan["rollback"],
        })

    def _read_restore_plan(self, operation_dir: Path) -> dict[str, Any]:
        path = self._restore_internal(operation_dir / "plan.json")
        plan = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise SproutError("invalid restore recovery plan")
        progress_path = self._restore_internal(operation_dir / "progress.json")
        if progress_path.exists():
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            if not isinstance(progress, dict) or set(progress) != {"attempted", "rollback"}:
                raise SproutError("invalid restore recovery progress")
            plan.update(progress)
        return plan

    def _finalize_materialization(
        self,
        target: dict[str, FileState],
        head_branch: str | None,
        *,
        partial: bool = False,
        current_commit: str | None | object = UNCHANGED,
    ) -> None:
        with self.connect() as db:
            if partial:
                db.executemany(
                    "DELETE FROM tracked_paths WHERE path_key=?", ((path_key(path),) for path in target)
                )
            else:
                db.execute("DELETE FROM tracked_paths")
            db.executemany(
                "INSERT INTO tracked_paths(path,path_key,file_id) VALUES(?,?,?)",
                ((path, path_key(path), item.file_id) for path, item in target.items()),
            )
            if head_branch is not None:
                db.execute("UPDATE repository_state SET head_branch_id=? WHERE id=1", (self._branch_id_from_db(db, head_branch),))
            if current_commit is not UNCHANGED:
                self._set_current_commit(db, current_commit)
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
                self._safe_restore_path(directory.relative_to(self.root).as_posix())
                directory.rmdir()
            except (OSError, SproutError):
                pass

    def _materialize(
        self,
        target: dict[str, FileState],
        *,
        head_branch: str | None = None,
        partial: bool = False,
        current_commit: str | None | object = UNCHANGED,
        _receipt: _MaterializationReceipt | None = None,
    ) -> None:
        current = self.tracked()
        plan = self._restore_plan(target, partial=partial)
        # Planning only reads the working tree; forget observations before rewriting it.
        self.worktree_cache.invalidate()
        self._verify_manifest(target)

        operation_id = "restore-" + uuid.uuid4().hex
        operation_dir = self._restore_internal(self.tmp / operation_id)
        operation_dir.mkdir()
        staged = operation_dir / "staged"
        active_registered = False
        operation_complete = False
        try:
            for relative, item in target.items():
                output = self._restore_internal(staged / Path(relative))
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("wb") as target_file:
                    self._copy_verified_object(item, target_file)
                    target_file.flush()
                    os.fsync(target_file.fileno())
            self._write_operation_plan(operation_dir / "plan.json", plan)
            active_registered = True
            self._set_active_operation(operation_id)
            for index, action in enumerate(plan["actions"]):
                plan["attempted"] = index + 1
                self._write_restore_progress(operation_dir, plan)
                self._apply_restore_action(operation_dir, action)
            self._finalize_materialization(
                target, head_branch, partial=partial, current_commit=current_commit
            )
            operation_complete = True  # DB commit is the commit point; never undo it.
            if not partial:
                self._remove_empty_parents(current - set(target))
                self._apply_saved_spellings(target)
        except Exception:
            if operation_complete:
                raise
            if active_registered:
                with self.connect() as db:
                    durable_active = db.execute(
                        "SELECT value FROM meta WHERE key='active_operation'"
                    ).fetchone()[0]
                if durable_active == "":
                    operation_complete = True
                    raise  # Finalization committed before reporting its error.
            try:
                if active_registered:
                    # Re-read the durable checkpoint, including when a write failed.
                    saved_plan = self._read_restore_plan(operation_dir)
                    self._rollback_materialization(operation_dir, saved_plan)
                    self._set_active_operation("")
                    active_registered = False
            except SproutError:
                raise  # Keep the structured path/conflict error and all backups.
            except Exception as rollback_exc:
                raise SproutError(
                    "restore failed and automatic rollback was incomplete; rerun Sprout to recover",
                    code="restore_rollback_incomplete",
                ) from rollback_exc
            raise
        finally:
            if _receipt is not None:
                _receipt.committed = operation_complete
                if active_registered and not operation_complete:
                    # BaseException can interrupt after the DB commit but before
                    # operation_complete is assigned. Inspect the durable marker.
                    try:
                        with self.connect() as db:
                            active = db.execute(
                                "SELECT value FROM meta WHERE key='active_operation'"
                            ).fetchone()[0]
                        _receipt.committed = active == ""
                    except (OSError, sqlite3.Error, SproutError):
                        _receipt.committed = None  # Keep the bud if outcome is unknown.
            if operation_complete or not active_registered:
                self._restore_tree_files(operation_dir)
                shutil.rmtree(operation_dir, ignore_errors=True)

    def _apply_saved_spellings(self, target: dict[str, FileState]) -> None:
        """Respell folders kept by a restore; a failure only leaves a reported rename."""
        for relative in target:
            actual = self._disk_spellings([relative])[relative]
            if actual is None or actual == relative:
                continue
            current = self.root
            try:
                for wanted, found in zip(relative.split("/"), actual.split("/")):
                    if wanted != found:
                        self._rename_file(current / found, current / wanted, respelling=True)
                    current = current / wanted
            except OSError:
                return

    def _snapshot_ids_match(self, db: sqlite3.Connection, commit_id: str,
                            signature: dict[str, tuple[str, int]]) -> bool:
        bindings = self.tracked_ids()
        return all(db.execute("SELECT file_id FROM commit_files WHERE commit_id=? AND path=?",
                              (commit_id, path)).fetchone()[0] == bindings.get(path) for path in signature)

    def _is_saved_snapshot(
        self, signature: dict[str, tuple[str, int]], *, exact: bool = True
    ) -> bool:
        if not exact:
            if not signature:
                return True
            with self.connect() as db:
                return any(self._snapshot_ids_match(db, candidate, signature)
                           for candidate in self._commits_containing_from_db(db, signature))

        return self._matching_saved_snapshot_commit(signature) is not None

    def _has_unsaved_changes(self, paths: set[str] | None = None) -> bool:
        self._adopt_disk_spellings()
        tracked = self.tracked()
        head = self.manifest(self.current_commit())
        if paths is not None:
            spelled = {path_key(path): path for path in tracked}
            paths = {spelled.get(path_key(path), path) for path in paths}
        if paths is None:
            hash_paths = tracked
            status_paths = tracked | set(head)
            exact = True
        else:
            hash_paths = tracked & paths
            status_paths = paths
            exact = False

        signature: dict[str, tuple[str, int]] | None = None
        if all((self.root / Path(relative)).is_file() for relative in hash_paths):
            signature = self._hash_worktree_files(hash_paths)

        bindings = self.tracked_ids()
        if any(p in head and bindings.get(p) != head[p].file_id for p in hash_paths):
            return True
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
            if (digest != head[relative].object_hash or size != head[relative].size
                    or bindings.get(relative) != head[relative].file_id):
                has_changes = True

        if not has_changes:
            return False
        if signature is None:
            return True
        return not self._is_saved_snapshot(signature, exact=exact)

    def _resolve_manifest_paths(
        self, values: list[Path], manifest: dict[str, FileState]
    ) -> set[str]:
        selected: set[str] = set()
        for value in values:
            relative = self._relative_file(value, must_exist=False)
            saved = {path_key(path): path for path in manifest}.get(path_key(relative))
            if saved is not None:
                selected.add(saved)
                continue
            prefix = path_key(relative.rstrip("/") + "/")
            matches = {path for path in manifest if path_key(path).startswith(prefix)}
            if not matches:
                raise SproutError(f"path not in commit: {relative}", code="path_not_in_commit", details={"path": str(relative)})
            selected.update(matches)
        return selected

    @staticmethod
    def _export_destination(output_root: Path, relative: str) -> Path:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise SproutError(f"export path escapes output directory: {relative}", code="export_unsafe_path", details={"path": str(relative)})
        destination = output_root / relative_path
        current = destination
        while current != output_root:
            if current.is_symlink():
                raise SproutError(f"symbolic link in export path: {relative}", code="export_unsafe_path", details={"path": str(relative)})
            current = current.parent
        try:
            destination.resolve(strict=False).relative_to(output_root)
        except ValueError as exc:
            raise SproutError(f"export path escapes output directory: {relative}", code="export_unsafe_path", details={"path": str(relative)}) from exc
        return destination

    def export(
        self,
        value: str,
        output: Path,
        paths: list[Path] | None = None,
        *,
        force: bool = False,
    ) -> ExportResult:
        commit_id = self.resolve_commit(value)
        commit_manifest = self.manifest(commit_id)
        selected = (
            self._resolve_manifest_paths(paths, commit_manifest)
            if paths
            else set(commit_manifest)
        )
        target = {path: commit_manifest[path] for path in sorted(selected)}
        output_root = output.resolve(strict=False)
        if output_root == self.control or self.control in output_root.parents:
            raise SproutError("cannot export into Sprout metadata", code="export_into_metadata")
        if output_root.exists() and not output_root.is_dir():
            raise SproutError(f"export output is not a directory: {output}", code="export_output_not_directory", details={"path": str(output)})

        tracked_keys = {self._path_key(path) for path in self.tracked()}
        destinations: dict[str, Path] = {}
        for relative in target:
            destination = self._export_destination(output_root, relative)
            try:
                working_relative = destination.relative_to(self.root).as_posix()
            except ValueError:
                working_relative = None
            if (
                working_relative is not None
                and self._path_key(working_relative) in tracked_keys
            ):
                raise SproutError(
                    f"export path would change tracked working file: {working_relative}",
                    code="export_would_change_tracked",
                    details={"path": str(working_relative)},
                )
            if destination.exists():
                if not destination.is_file():
                    raise SproutError(f"cannot overwrite non-file export path: {relative}", code="export_path_not_file", details={"path": str(relative)})
                if not force:
                    raise SproutError(f"output file already exists: {relative}", code="export_output_exists", details={"path": str(relative)})
            destinations[relative] = destination

        self._verify_manifest(target)
        output_root.mkdir(parents=True, exist_ok=True)
        for relative, item in target.items():
            destination = destinations[relative]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not force:
                try:
                    with destination.open("xb") as target_file:
                        self._copy_verified_object(item, target_file)
                        target_file.flush()
                        os.fsync(target_file.fileno())
                    os.utime(
                        destination,
                        ns=(item.mtime_ns, item.mtime_ns),
                    )
                except FileExistsError as exc:
                    raise SproutError(
                        f"output file already exists: {relative}",
                        code="export_output_exists",
                        details={"path": str(relative)},
                    ) from exc
                except Exception:
                    destination.unlink(missing_ok=True)
                    raise
                continue

            fd, temp_name = tempfile.mkstemp(
                dir=destination.parent,
                prefix=".sprout-export-",
            )
            try:
                with os.fdopen(fd, "wb") as target_file:
                    self._copy_verified_object(item, target_file)
                    target_file.flush()
                    os.fsync(target_file.fileno())
                os.utime(temp_name, ns=(item.mtime_ns, item.mtime_ns))
                os.replace(temp_name, destination)
            except Exception:
                Path(temp_name).unlink(missing_ok=True)
                raise
        return ExportResult(commit_id, tuple(target))

    def cat(self, value: str, path: Path, target: BinaryIO) -> str:
        commit_id = self.resolve_commit(value)
        commit_manifest = self.manifest(commit_id)
        relative = self._relative_file(path, must_exist=False)
        item = commit_manifest.get(relative)
        if item is None:
            raise SproutError(f"path not in commit: {relative}", code="path_not_in_commit", details={"path": str(relative)})
        self._copy_verified_object(item)
        self._copy_verified_object(item, target)
        return commit_id

    @staticmethod
    def _archive_attachment_json(
        attachment: CommitAttachment, archive_path: str
    ) -> dict[str, Any]:
        return {
            "id": attachment.id,
            "role": attachment.role,
            "position": attachment.position,
            "original_name": attachment.original_name,
            "display_name": attachment.display_name, "description": attachment.description,
            "media_type": attachment.media_type,
            "size": attachment.size,
            "sha256": attachment.object_hash,
            "created_at": attachment.created_at,
            "updated_at": attachment.updated_at,
            "archive_path": archive_path,
        }

    def _archive_model(self) -> tuple[dict[str, Any], list[_ArchiveCopy]]:
        """Read every commit, including unreachable ones, from one SQLite snapshot."""
        with self.connect() as db:
            db.execute("BEGIN")
            metadata = {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM meta")}
            commit_rows = list(db.execute("SELECT * FROM commits ORDER BY seq DESC"))
            commit_ids = [row["id"] for row in commit_rows]
            files: dict[str, list[FileState]] = {commit_id: [] for commit_id in commit_ids}
            for row in db.execute(
                "SELECT commit_id, path, object_hash, size, mtime_ns, file_id "
                "FROM commit_files ORDER BY commit_id, path"
            ):
                self._validate_file_time(row["mtime_ns"], row["path"])
                files[row["commit_id"]].append(
                    FileState(row["path"], row["object_hash"], row["size"], row["mtime_ns"], row["file_id"])
                )
            attachments = self._attachments_many_from_db(db, commit_ids)
            annotations = self._annotations_many_from_db(db, commit_ids)
            branch_rows = list(
                db.execute(
                    "SELECT id, name, commit_id, comment, deleted, created_at, deleted_at "
                    "FROM branches ORDER BY deleted, name, id"
                )
            )
            tag_rows = list(db.execute("SELECT name, commit_id, comment, created_at FROM tags ORDER BY name"))
            state = db.execute(
                "SELECT head_branch_id, current_commit_id FROM repository_state WHERE id=1"
            ).fetchone()

        short_names = [
            static_archive.snapshot_directory_name(row["created_at"], row["id"]) for row in commit_rows
        ]
        children: dict[str, list[str]] = {commit_id: [] for commit_id in commit_ids}
        for row in reversed(commit_rows):
            if row["parent_id"] is not None and row["parent_id"] in children:
                children[row["parent_id"]].append(row["id"])

        copies: list[_ArchiveCopy] = []
        commits: list[dict[str, Any]] = []
        for row, short_name in zip(commit_rows, short_names):
            commit_id = row["id"]
            name = (
                short_name
                if short_names.count(short_name) == 1
                else static_archive.snapshot_directory_name(row["created_at"], commit_id, len(commit_id))
            )
            directory = f"snapshots/{name}"
            file_entries = []
            for item in files[commit_id]:
                parts = item.path.split("/")
                if Path(item.path).is_absolute() or any(part in {"", ".", ".."} for part in parts):
                    raise SproutError(f"commit {commit_id[:12]} has an unsafe path: {item.path}")
                archive_path = f"{directory}/files/{item.path}"
                file_entries.append(
                    {"path": item.path, "file_id": item.file_id, "size": item.size, "sha256": item.object_hash, "archive_path": archive_path}
                )
                copies.append(
                    _ArchiveCopy(
                        archive_path,
                        item,
                        {"commit_id": commit_id, "path": item.path, "object_hash": item.object_hash},
                    )
                )
            thumbnail = None
            previews = []
            for attachment in attachments[commit_id]:
                file_name = static_archive.safe_file_name(attachment.original_name)
                if attachment.role == THUMBNAIL_ROLE:
                    archive_path = f"{directory}/attachments/thumbnail/{attachment.id}/{file_name}"
                    thumbnail = self._archive_attachment_json(attachment, archive_path)
                else:
                    archive_path = (
                        f"{directory}/attachments/previews/"
                        f"{attachment.position + 1:03d}_{attachment.id}/{file_name}"
                    )
                    previews.append(self._archive_attachment_json(attachment, archive_path))
                copies.append(
                    _ArchiveCopy(
                        archive_path,
                        FileState(attachment.original_name, attachment.object_hash, attachment.size, 0),
                        {
                            "commit_id": commit_id,
                            "attachment_id": attachment.id,
                            "role": attachment.role,
                            "original_name": attachment.original_name,
                            "object_hash": attachment.object_hash,
                        },
                    )
                )
            commits.append(
                {
                    "id": commit_id,
                    "seq": row["seq"],
                    "parent_id": row["parent_id"],
                    "children_ids": children[commit_id],
                    "branch_id": row["branch_id"],
                    "branch_name": row["branch_name"],
                    "created_at": row["created_at"],
                    "message": row["message"],
                    "note": annotations[commit_id].note,
                    "note_updated_at": annotations[commit_id].note_updated_at,
                    "labels": list(annotations[commit_id].labels),
                    "directory": directory,
                    "files": file_entries,
                    "thumbnail": thumbnail,
                    "previews": previews,
                }
            )

        model = {
            "format": static_archive.ARCHIVE_FORMAT,
            "format_version": static_archive.ARCHIVE_FORMAT_VERSION,
            "generator": f"sprout {__version__}",
            "generated_at": utc_timestamp(),
            "repository": {
                "repository_id": metadata["repository_id"],
                "repository_created_at": metadata["repository_created_at"],
                "schema_version": metadata["schema_version"],
            },
            "current_branch_id": state["head_branch_id"],
            "current_commit_id": state["current_commit_id"],
            "branches": [
                {
                    "id": branch["id"],
                    "name": branch["name"],
                    "commit_id": branch["commit_id"],
                    "comment": branch["comment"],
                    "created_at": branch["created_at"],
                    "deleted_at": branch["deleted_at"],
                    "deleted": bool(branch["deleted"]),
                }
                for branch in branch_rows
            ],
            "tags": [
                {
                    "name": tag["name"],
                    "commit_id": tag["commit_id"],
                    "comment": tag["comment"],
                    "created_at": tag["created_at"],
                }
                for tag in tag_rows
            ],
            "commits": commits,
        }
        return model, copies

    def plan_archive(self, output: Path) -> ArchivePlan:
        """Validate the destination and size every file a static archive would write."""
        output_root = output.resolve(strict=False)
        if output_root == self.control or self.control in output_root.parents:
            raise SproutError("cannot archive into Sprout metadata")
        if output_root == self.root or output_root in self.root.parents:
            raise SproutError("archive output must not contain the project")
        if output_root.exists() and not output_root.is_dir():
            raise SproutError(f"archive output is not a directory: {output}", code="archive_output_exists")
        if output_root.is_dir() and any(output_root.iterdir()):
            raise SproutError(
                f"archive output is not empty: {output}",
                code="archive_output_not_empty",
                details={"output": str(output_root)},
            )
        staging = output_root.with_name(f".{output_root.name}{static_archive.INCOMPLETE_SUFFIX}")
        removes_incomplete = False
        if staging.exists() or staging.is_symlink():
            if staging.is_symlink() or not (staging / static_archive.INCOMPLETE_MARKER).is_file():
                raise SproutError(
                    f"unrecognized path where the incomplete archive is staged: {staging}",
                    code="archive_staging_conflict",
                    details={"staging": str(staging)},
                )
            removes_incomplete = True

        model, copies = self._archive_model()
        view = {
            **model,
            "commits_by_id": {commit["id"]: commit for commit in model["commits"]},
            "branches_by_id": {branch["id"]: branch for branch in model["branches"]},
        }
        texts = {
            "index.html": static_archive.render_index(view),
            "archive.json": static_archive.to_json(model),
            "README.txt": static_archive.render_readme(model),
        }
        for commit in model["commits"]:
            texts[f"{commit['directory']}/index.html"] = static_archive.render_commit(view, commit)
            texts[f"{commit['directory']}/commit.json"] = static_archive.to_json(commit)
        encoded = {path: text.encode("utf-8") for path, text in texts.items()}
        total = sum(len(data) for data in encoded.values()) + sum(copy.item.size for copy in copies)

        existing = output_root
        while not existing.exists():
            existing = existing.parent
        return ArchivePlan(
            output=output_root,
            staging=staging,
            commits=len(model["commits"]),
            files=len(encoded) + len(copies),
            bytes=total,
            free_bytes=shutil.disk_usage(existing).free,
            removes_incomplete=removes_incomplete,
            texts=encoded,
            copies=tuple(copies),
        )

    @staticmethod
    def _extended_path(path: Path) -> Path:
        if os.name != "nt":
            return path
        text = str(path)
        if text.startswith("\\\\?\\"):
            return path
        if text.startswith("\\\\"):
            return Path("\\\\?\\UNC\\" + text[2:])
        return Path("\\\\?\\" + text)

    def archive(self, output: Path) -> ArchivePlan:
        """Expand every commit into a static archive that appears only when complete."""
        plan = self.plan_archive(output)
        if not plan.sufficient_space:
            raise SproutError(
                f"not enough free space for archive: needs {plan.bytes} bytes, "
                f"{plan.free_bytes} bytes available",
                code="archive_insufficient_space",
                details={"required_bytes": plan.bytes, "free_bytes": plan.free_bytes},
            )
        # Deep snapshot paths easily exceed MAX_PATH on Windows.
        staging = self._extended_path(plan.staging)
        output = self._extended_path(plan.output)
        if plan.removes_incomplete:
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        marker = staging / static_archive.INCOMPLETE_MARKER
        marker.write_bytes(
            b"This Sprout archive was interrupted before completion and is incomplete.\n"
            b"Rerun 'sprout archive' with the same output to replace it.\n"
        )
        try:
            extracted: dict[tuple[str, int], Path] = {}
            for copy in plan.copies:
                destination = staging / copy.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                key = (copy.item.object_hash, copy.item.size)
                if key in extracted:
                    shutil.copyfile(extracted[key], destination)
                else:
                    try:
                        with destination.open("xb") as target:
                            self._copy_verified_object(copy.item, target)
                    except SproutError as exc:
                        subject = (
                            f"file {copy.details['path']}"
                            if "path" in copy.details
                            else f"{copy.details['role']} {copy.details['attachment_id']} "
                            f"({copy.details['original_name']})"
                        )
                        raise SproutError(
                            f"archive aborted: {subject} of commit "
                            f"{copy.details['commit_id'][:12]}: {exc}",
                            code="archive_object_invalid",
                            details=copy.details,
                        ) from exc
                    extracted[key] = destination
                if "path" in copy.details:
                    os.utime(destination, ns=(copy.item.mtime_ns, copy.item.mtime_ns))
            for relative, data in plan.texts.items():
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            marker.unlink()
            if output.is_dir():
                output.rmdir()
            os.rename(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return plan

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
            for value_path in paths:
                absolute = Path(os.path.abspath(value_path))
                try:
                    relative = absolute.relative_to(self.root).as_posix()
                except ValueError as exc:
                    raise SproutError(
                        f"unsafe restore path: {value_path}", code="unsafe_restore_path",
                        details={"path": str(value_path), "reason": "path is outside the repository"},
                    ) from exc
                self._safe_restore_path(relative)
            selected = self._resolve_manifest_paths(paths, commit_manifest)
            target = {path: commit_manifest[path] for path in selected}
            self._validate_restore_inputs(target, partial=True)
            self._restore_plan(target, partial=True)
            dirty = self._has_unsaved_changes(selected)
            if dirty and not discard:
                raise SproutError(
                    "working tree has uncommitted changes (use --discard to replace them)",
                    code="uncommitted_changes",
                    details={"can_discard": True},
                )
            self._materialize_keeping_discarded(target, dirty, partial=True)
        else:
            self._validate_restore_inputs(commit_manifest)
            dirty = self._has_unsaved_changes()
            if dirty and not discard:
                raise SproutError(
                    "working tree has uncommitted changes (use --discard to replace them)",
                    code="uncommitted_changes",
                    details={"can_discard": True},
                )
            self._materialize_keeping_discarded(commit_manifest, dirty, current_commit=commit_id)
        return commit_id

    @locked
    def switch(self, name: str, *, discard: bool = False) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT commit_id FROM branches WHERE name=? AND deleted=0", (name,)).fetchone()
        if row is None:
            raise SproutError(f"unknown branch: {name}", code="unknown_branch", details={"name": name})
        target = self.manifest(row[0])
        self._validate_restore_inputs(target)
        dirty = self._has_unsaved_changes()
        if dirty and not discard:
            raise SproutError(
                "working tree has uncommitted changes (use --discard to replace them)",
                code="uncommitted_changes",
                details={"can_discard": True},
            )
        self._materialize_keeping_discarded(target, dirty, head_branch=name, current_commit=row[0])
        return row[0]

    def _buds_from_db(self, db: sqlite3.Connection, bud_ids: list[str] | None = None) -> list[Bud]:
        query = "SELECT id, base_commit_id, branch_id, branch_name, created_at, name FROM buds"
        params: tuple[str, ...] = ()
        if bud_ids is not None:
            query += f" WHERE id IN ({','.join('?' for _ in bud_ids)})"
            params = tuple(bud_ids)
        rows = list(db.execute(query + " ORDER BY seq DESC", params))
        files: dict[str, list[FileState]] = {row["id"]: [] for row in rows}
        for row in db.execute(
            "SELECT bud_id, path, object_hash, size, mtime_ns, file_id FROM bud_files ORDER BY path"
        ):
            if row["bud_id"] in files:
                files[row["bud_id"]].append(
                    FileState(row["path"], row["object_hash"], row["size"], row["mtime_ns"], row["file_id"])
                )
        buds: list[Bud] = []
        for row in rows:
            base = self._manifest_from_db(db, row["base_commit_id"])
            changes = self.diff_manifests(base, {item.path: item for item in files[row["id"]]})
            buds.append(
                Bud(
                    id=row["id"],
                    branch_id=row["branch_id"],
                    base_commit_id=row["base_commit_id"],
                    branch_name=row["branch_name"],
                    created_at=row["created_at"],
                    files=tuple(files[row["id"]]),
                    changes=tuple(StatusEntry(entry.state, entry.path, entry.previous_path) for entry in changes),
                    name=row["name"],
                )
            )
        return buds

    def buds(self) -> list[Bud]:
        """Return saved buds, newest first."""
        with self.connect() as db:
            return self._buds_from_db(db)

    def resolve_bud(self, value: str) -> str:
        if not HEX_COMMIT_REFERENCE.fullmatch(value):
            raise SproutError(f"unknown bud: {value}", code="unknown_bud")
        with self.connect() as db:
            matches = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM buds WHERE substr(id, 1, ?) = ?", (len(value), value)
                )
            ]
        if not matches:
            raise SproutError(f"unknown bud: {value}", code="unknown_bud")
        if len(matches) > 1:
            raise SproutError(f"ambiguous bud: {value}", code="ambiguous_bud")
        return matches[0]

    @staticmethod
    def _normalize_bud_name(name: str) -> str:
        normalized = unicodedata.normalize("NFC", name).strip()
        if len(normalized) > 256 or any(character in normalized for character in "\r\n\x00"):
            raise SproutError(
                "bud name must be one line of 256 characters or fewer", code="invalid_bud_name"
            )
        return normalized

    def _save_bud(self, name: str = "") -> Bud:
        name = self._normalize_bud_name(name)
        base = self.current_commit()
        files, _ = self._store_tracked_files("saving a bud")
        base_signature = {
            path: (state.object_hash, state.size, state.file_id) for path, state in self.manifest(base).items()
        }
        if {item.path: (item.object_hash, item.size, item.file_id) for item in files} == base_signature:
            raise SproutError("no unsaved changes to keep in a bud", code="nothing_to_save")
        bud_id = uuid.uuid4().hex
        created_at = utc_timestamp()
        branch_id, branch_name = self.branch_id(), self.head_branch()
        with self.connect() as db:
            self._register_objects(db, {item.object_hash: item.size for item in files}, created_at)
            db.execute(
                "INSERT INTO buds(id, seq, base_commit_id, branch_id, branch_name, created_at, name) "
                "VALUES(?, ?, ?, ?, ?, ?, ?)",
                (bud_id, recovery.next_seq(db, "buds"), base, branch_id, branch_name, created_at, name),
            )
            db.executemany(
                "INSERT INTO bud_files(bud_id, path, path_key, object_hash, size, mtime_ns, file_id) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    (bud_id, item.path, path_key(item.path), item.object_hash, item.size, item.mtime_ns, item.file_id)
                    for item in files
                ),
            )
            return self._buds_from_db(db, [bud_id])[0]

    @locked
    def save_bud(self, name: str = "") -> Bud:
        """Keep the unsaved tracked changes as a bud on the current snapshot."""
        return self._save_bud(name)

    @locked
    def move_changes_to_bud(self, name: str = "") -> Bud:
        """Move the unsaved tracked changes into a bud, returning the files to the current snapshot."""
        if not self._has_unsaved_changes():
            raise SproutError("no unsaved changes to keep in a bud", code="nothing_to_save")
        current = self.current_commit()
        bud = self._materialize_keeping_changes(
            self.manifest(current), head_branch=None, current_commit=current, name=name
        )
        assert bud is not None
        return bud

    @locked
    def rename_bud(self, value: str, name: str) -> Bud:
        """Set or, with an empty name, clear the name of a bud."""
        bud_id = self.resolve_bud(value)
        normalized = self._normalize_bud_name(name)
        with self.connect() as db:
            db.execute("UPDATE buds SET name=? WHERE id=?", (normalized, bud_id))
            return self._buds_from_db(db, [bud_id])[0]

    @locked
    def restore_bud(self, value: str) -> tuple[Bud, Bud | None]:
        """Bring a bud back into the working tree, keeping any newer changes as a bud."""
        bud_id = self.resolve_bud(value)
        with self.connect() as db:
            bud = self._buds_from_db(db, [bud_id])[0]
            branch = db.execute(
                "SELECT name FROM branches WHERE id=? AND deleted=0", (bud.branch_id,)
            ).fetchone()
        stashed = self._materialize_keeping_changes(
            {item.path: item for item in bud.files},
            head_branch=branch[0] if branch is not None else None,
            current_commit=bud.base_commit_id,
        )
        with self.connect() as db:
            db.execute("DELETE FROM buds WHERE id=?", (bud.id,))
        return bud, stashed

    def _materialize_keeping_changes(
        self,
        target: dict[str, FileState],
        *,
        head_branch: str | None,
        current_commit: str | None,
        name: str = "",
    ) -> Bud | None:
        """Replace the whole working tree, first keeping unsaved changes as a bud."""
        self._validate_restore_inputs(target)
        self._restore_plan(target, partial=False)
        for item in target.values():
            self._check_object_encoding(item.object_hash)
        stashed = self._save_bud(name) if self._has_unsaved_changes() else None
        receipt = _MaterializationReceipt()
        try:
            self._materialize(
                target, head_branch=head_branch, current_commit=current_commit, _receipt=receipt
            )
        except BaseException:
            # Uncommitted restores roll back from their durable backups. Once the
            # restore committed, the new bud is the only copy of the previous work.
            if stashed is not None and receipt.committed is False:
                with self.connect() as db:
                    db.execute("DELETE FROM buds WHERE id=?", (stashed.id,))
            raise
        return stashed

    def _materialize_keeping_discarded(
        self, target: dict[str, FileState], dirty: bool, **options: Any
    ) -> None:
        """Restore over unsaved work, keeping that work in the trash as a bud."""
        self._restore_plan(target, partial=options.get("partial", False))
        for item in target.values():
            self._check_object_encoding(item.object_hash)
        item_id = self._trash_discarded_work() if dirty else None
        receipt = _MaterializationReceipt()
        try:
            self._materialize(target, _receipt=receipt, **options)
        except BaseException:
            # Nothing was discarded unless the restore committed.
            if item_id is not None and receipt.committed is False:
                self._return_discarded_work(item_id)
            raise

    def _trash_discarded_work(self) -> str | None:
        try:
            bud = self._save_bud()
        except SproutError as exc:
            if exc.code == "nothing_to_save":
                return None
            raise
        with self.connect() as db:
            return self._trash_bud(db, bud, "discard")

    def _return_discarded_work(self, item_id: str) -> None:
        """Forget a recovery item whose restore never replaced the working files."""
        with self.connect() as db:
            db.execute("DELETE FROM trash_entries WHERE id=?", (item_id,))

    @staticmethod
    def _trash_bud(db: sqlite3.Connection, bud: Bud, kind: str) -> str:
        before = recovery.capture_bud(db, bud.id)
        db.execute("DELETE FROM buds WHERE id=?", (bud.id,))
        paths = [entry.path for entry in bud.changes]
        summary = f"{paths[0]} +{len(paths) - 1}" if len(paths) > 1 else (paths[0] if paths else bud.id[:12])
        return recovery.record(db, before, kind, bud.name or summary, bud.id, utc_timestamp())

    @locked
    def go(self, value: str) -> GoResult:
        """Move to a snapshot, keeping unsaved changes as a bud on the current one."""
        commit_id = self.resolve_commit(value)
        with self.connect() as db:
            current_branch = db.execute(
                "SELECT b.name FROM branches b JOIN repository_state s ON s.head_branch_id=b.id WHERE s.id=1"
            ).fetchone()[0]
            tips = [
                row[0]
                for row in db.execute(
                    "SELECT name FROM branches WHERE deleted=0 AND commit_id=? ORDER BY name", (commit_id,)
                )
            ]
        if current_branch in tips:
            branch = current_branch
        elif value in tips:
            branch = value
        elif tips:
            branch = tips[0]
        else:
            branch = current_branch
        stashed = self._materialize_keeping_changes(
            self.manifest(commit_id),
            head_branch=branch if branch != current_branch else None,
            current_commit=commit_id,
        )
        head = self.head_position()
        # The tracked files now match the target exactly, so there is nothing to re-hash.
        return GoResult(
            commit_id=commit_id,
            branch=head.branch,
            branch_id=head.branch_id,
            at_branch_tip=head.at_branch_tip,
            bud=stashed,
            changes=(),
        )

    @locked
    def drop_bud(self, value: str) -> Bud:
        """Move a bud to the trash."""
        bud_id = self.resolve_bud(value)
        with self.connect() as db:
            bud = self._buds_from_db(db, [bud_id])[0]
            self._trash_bud(db, bud, "bud_delete")
        return bud
