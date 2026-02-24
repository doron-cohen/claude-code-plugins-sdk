"""In-memory adapters for testing (no disk I/O)."""

from __future__ import annotations

from pathlib import Path

from ..models.state import BlocklistFile, KnownMarketplaceEntry


def _default_blocklist() -> BlocklistFile:
    from datetime import datetime, timezone

    return BlocklistFile(fetchedAt=datetime(1970, 1, 1, tzinfo=timezone.utc), plugins=[])


class InMemoryMarketplaceAdapter:
    def __init__(
        self,
        marketplaces: dict[str, KnownMarketplaceEntry] | None = None,
        blocklist: BlocklistFile | None = None,
    ) -> None:
        self._marketplaces = dict(marketplaces or {})
        self._blocklist = blocklist if blocklist is not None else _default_blocklist()
        self._cache: dict[str, dict] = {}

    def get_marketplaces(self) -> dict[str, KnownMarketplaceEntry]:
        return dict(self._marketplaces)

    def set_marketplaces(self, data: dict[str, KnownMarketplaceEntry]) -> None:
        self._marketplaces = dict(data)

    def get_blocklist(self) -> BlocklistFile:
        return self._blocklist

    def get_cache_path(self, name: str) -> Path:
        if name in self._cache:
            return Path(self._cache[name]["source_path"])
        return Path(f"/in-memory/marketplaces/{name}")

    def store_cache(self, name: str, source_path: Path) -> Path:
        path = Path(source_path)
        self._cache[name] = {"source_path": str(path)}
        return path

    def delete_cache(self, name: str) -> None:
        self._cache.pop(name, None)


class InMemorySettingsAdapter:
    def __init__(self, enabled_plugins: dict[str, bool] | None = None) -> None:
        self._enabled_plugins = dict(enabled_plugins or {})

    def get_enabled_plugins(self) -> dict[str, bool]:
        return dict(self._enabled_plugins)

    def set_enabled_plugins(self, data: dict[str, bool]) -> None:
        self._enabled_plugins = dict(data)
