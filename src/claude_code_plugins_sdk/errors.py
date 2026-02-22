from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class LoadError(Exception):
    """Raised when loading a plugin, marketplace, or component file fails.

    Attributes:
        path: The file or directory path that could not be loaded, if applicable.
    """

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        super().__init__(message)


class FetchError(Exception):
    """Raised when a remote fetch fails (network, git, HTTP error, timeout).

    Attributes:
        url: The URL or source that failed, if applicable.
    """

    def __init__(self, message: str, url: str | None = None) -> None:
        self.url = url
        super().__init__(message)
