"""In-memory adapters for testing (no disk I/O)."""

from __future__ import annotations

import shutil
import tempfile
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
        self._plugin_cache: dict[tuple[str, str], Path] = {}
        self._plugin_cache_tmpdirs: list[tempfile.TemporaryDirectory] = []

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

    def store_plugin_cache(self, marketplace: str, plugin_name: str, source_path: Path) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self._plugin_cache_tmpdirs.append(tmpdir)
        dest = Path(tmpdir.name) / plugin_name
        shutil.copytree(source_path, dest)
        self._plugin_cache[(marketplace, plugin_name)] = dest
        return dest

    def get_plugin_cache_path(self, marketplace: str, plugin_name: str) -> Path:
        if (marketplace, plugin_name) in self._plugin_cache:
            return self._plugin_cache[(marketplace, plugin_name)]
        return Path(f"/in-memory/plugin-cache/{marketplace}/{plugin_name}")

    def delete_plugin_cache(self, marketplace: str, plugin_name: str) -> None:
        path = self._plugin_cache.pop((marketplace, plugin_name), None)
        if path is not None and path.is_dir():
            shutil.rmtree(path)


class InMemorySettingsAdapter:
    def __init__(self, enabled_plugins: dict[str, bool] | None = None) -> None:
        self._enabled_plugins = dict(enabled_plugins or {})

    def get_enabled_plugins(self) -> dict[str, bool]:
        return dict(self._enabled_plugins)

    def set_enabled_plugins(self, data: dict[str, bool]) -> None:
        self._enabled_plugins = dict(data)
