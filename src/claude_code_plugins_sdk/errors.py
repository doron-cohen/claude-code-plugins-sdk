from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class LoadError(Exception):
    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        super().__init__(message)
