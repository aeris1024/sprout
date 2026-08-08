from __future__ import annotations

from typing import Any


class SproutError(Exception):
    """An expected, user-facing Sprout error with machine-readable metadata."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "sprout_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}
