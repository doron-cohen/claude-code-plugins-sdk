"""Protocols (ports) for the plugin manager."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..models.state import BlocklistFile, KnownMarketplaceEntry


class MarketplaceStateAdapter(Protocol):
    """Manages the marketplace registry and file cache (~/.claude/plugins/)."""

    def get_marketplaces(self) -> dict[str, KnownMarketplaceEntry]: ...
    def set_marketplaces(self, data: dict[str, KnownMarketplaceEntry]) -> None: ...
    def get_blocklist(self) -> BlocklistFile: ...
    def get_cache_path(self, name: str) -> Path: ...
    def store_cache(self, name: str, source_path: Path) -> Path: ...
    def delete_cache(self, name: str) -> None: ...


class PluginSettingsAdapter(Protocol):
    """Manages enabledPlugins in a single settings.json (one per scope)."""

    def get_enabled_plugins(self) -> dict[str, bool]: ...
    def set_enabled_plugins(self, data: dict[str, bool]) -> None: ...


class FetchAdapter(Protocol):
    """Fetches a marketplace source to a local directory. Caller copies then exits context."""

    def fetch(self, source: str | object) -> AbstractContextManager[Path]: ...

    # source: str | AnyMarketplaceSource; object avoids circular import
