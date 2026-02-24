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


class AlreadyInstalledError(Exception):
    """Raised when installing a plugin that is already in enabledPlugins."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Plugin already installed: {key}")


class NotInstalledError(Exception):
    """Raised when uninstalling/enabling/disabling a plugin that is not installed."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Plugin not installed: {key}")


class MarketplaceNotFoundError(Exception):
    """Raised when a marketplace name is not in known_marketplaces."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Marketplace not found: {name}")


class PluginNotFoundError(Exception):
    """Raised when a plugin name is not in the marketplace manifest."""

    def __init__(self, name: str, marketplace: str) -> None:
        self.name = name
        self.marketplace = marketplace
        super().__init__(f"Plugin {name} not found in marketplace {marketplace}")


class PluginBlockedError(Exception):
    """Raised when installing a plugin that is on the blocklist."""

    def __init__(self, key: str, reason: str | None = None) -> None:
        self.key = key
        self.reason = reason
        msg = f"Plugin is blocked: {key}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)
