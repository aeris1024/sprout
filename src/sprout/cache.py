"""Disposable worktree observations, independent of the repository schema."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

from .errors import SproutError


CACHE_SCHEMA = """
CREATE TABLE binding (token TEXT NOT NULL);
CREATE TABLE worktree_cache (
    path TEXT PRIMARY KEY NOT NULL,
    size INTEGER NOT NULL CHECK (typeof(size)='integer' AND size >= 0),
    mtime_ns INTEGER NOT NULL CHECK (typeof(mtime_ns)='integer'),
    ctime_ns INTEGER NOT NULL CHECK (typeof(ctime_ns)='integer'),
    file_id TEXT NOT NULL,
    object_hash TEXT NOT NULL CHECK (length(object_hash)=64 AND object_hash NOT GLOB '*[^0-9a-f]*'),
    recorded_ns INTEGER NOT NULL CHECK (typeof(recorded_ns)='integer')
);
PRAGMA user_version=1;
"""


@lru_cache(maxsize=1)
def expected_cache_schema() -> dict[str, str]:
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(CACHE_SCHEMA)
        return dict(db.execute("SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL"))


class InvalidCache(Exception):
    """An obsolete or invalid disposable database may be recreated."""


class WorktreeCache:
    def __init__(self, path: Path, history: Path, validate: Callable[[Path], Path]):
        self.path = path
        self.history = history
        self.validate = validate

    def _token(self) -> str:
        # A failed invalidation cannot revive stale rows after a later reopen.
        # Any history write conservatively expires observations, including moves
        # and restores. This is independent of the cache's own schema version.
        info = self.history.stat()
        return repr((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))

    def _connect(self) -> sqlite3.Connection:
        for suffix in ("", "-journal", "-wal", "-shm"):
            self.validate(Path(str(self.path) + suffix))
        token = self._token()
        for attempt in range(2):
            db = sqlite3.connect(self.path, timeout=0)
            db.row_factory = sqlite3.Row
            try:
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version != 1:
                    raise InvalidCache("unsupported cache version")
                schema = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL"))
                if schema != expected_cache_schema() or db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise InvalidCache("invalid cache structure")
                binding = db.execute("SELECT token FROM binding").fetchall()
                if len(binding) != 1 or binding[0][0] != token:
                    with db:
                        db.execute("DELETE FROM worktree_cache")
                        db.execute("DELETE FROM binding")
                        db.execute("INSERT INTO binding VALUES(?)", (token,))
                return db
            except (sqlite3.Error, InvalidCache) as exc:
                db.close()
                corrupt = isinstance(exc, InvalidCache) or getattr(exc, "sqlite_errorcode", 0) in {
                    sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB,
                }
                if not corrupt or attempt:
                    raise
                # Only the disposable file is replaced; history is never repaired.
                self.path.unlink(missing_ok=True)
                with closing(sqlite3.connect(self.path, timeout=0)) as fresh:
                    fresh.executescript(CACHE_SCHEMA)
        raise AssertionError("unreachable")

    def get(self, path: str) -> dict[str, Any] | None:
        try:
            with closing(self._connect()) as db:
                row = db.execute("SELECT * FROM worktree_cache WHERE path=?", (path,)).fetchone()
                return dict(row) if row is not None else None
        except (OSError, sqlite3.Error, SproutError, InvalidCache):
            return None

    def lookup(self, paths: Iterable[str]) -> dict[str, dict[str, Any]]:
        """Read many observations through one connection; unusable caches read as empty."""
        try:
            with closing(self._connect()) as db:
                rows = (db.execute("SELECT * FROM worktree_cache WHERE path=?", (p,)).fetchone()
                        for p in paths)
                return {row["path"]: dict(row) for row in rows if row is not None}
        except (OSError, sqlite3.Error, SproutError, InvalidCache):
            return {}

    def put(self, path: str, *, size: int, mtime_ns: int, ctime_ns: int,
            file_id: str, object_hash: str, recorded_ns: int) -> None:
        self.record([{"path": path, "size": size, "mtime_ns": mtime_ns, "ctime_ns": ctime_ns,
                      "file_id": file_id, "object_hash": object_hash, "recorded_ns": recorded_ns}])

    def record(self, entries: Iterable[dict[str, Any]]) -> None:
        entries = list(entries)
        if not entries:
            return
        try:
            with closing(self._connect()) as db, db:
                db.executemany(
                    "INSERT OR REPLACE INTO worktree_cache VALUES"
                    "(:path,:size,:mtime_ns,:ctime_ns,:file_id,:object_hash,:recorded_ns)",
                    entries,
                )
        except (OSError, sqlite3.Error, SproutError, InvalidCache):
            pass

    def invalidate(self, paths: Iterable[str] | None = None) -> None:
        try:
            if not self.path.exists():
                return
            with closing(self._connect()) as db, db:
                if paths is None:
                    db.execute("DELETE FROM worktree_cache")
                else:
                    db.executemany("DELETE FROM worktree_cache WHERE path=?", ((p,) for p in paths))
        except (OSError, sqlite3.Error, SproutError, InvalidCache):
            pass
