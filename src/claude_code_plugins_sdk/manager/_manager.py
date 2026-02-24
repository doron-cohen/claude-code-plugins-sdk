"""PluginManager — domain logic for install, uninstall, marketplaces, updates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from ..errors import (
    AlreadyInstalledError,
    MarketplaceNotFoundError,
    NotInstalledError,
    PluginBlockedError,
    PluginNotFoundError,
)
from ..loaders.marketplace import load_marketplace
from ..models.marketplace import MarketplaceManifest
from ..models.state import (
    BlocklistFile,
    GitHubMarketplaceSource,
    GitMarketplaceSource,
    HttpMarketplaceSource,
    KnownMarketplaceEntry,
)
from ._protocols import FetchAdapter, MarketplaceStateAdapter, PluginSettingsAdapter

Scope = Literal["user", "project", "local"]


@dataclass
class InstalledPlugin:
    name: str
    marketplace: str
    enabled: bool
    scope: Scope

    @property
    def key(self) -> str:
        return f"{self.name}@{self.marketplace}"


@dataclass
class UpdateCheckResult:
    plugin_name: str
    marketplace: str
    current_version: str | None
    latest_version: str | None
    has_update: bool


def _plugin_key(plugin_name: str, marketplace: str) -> str:
    return f"{plugin_name}@{marketplace}"


def _source_to_state_source(source: object):
    """Convert fetcher source types to state AnyMarketplaceSource."""
    from ..fetchers._dispatcher import _detect
    from ..models.marketplace import GitHubSource, HTTPSource, URLSource
    from ..models.state import DirectoryMarketplaceSource, HostPatternMarketplaceSource

    if isinstance(source, str):
        source = _detect(source)
    if isinstance(source, GitHubSource):
        return GitHubMarketplaceSource(source="github", repo=source.repo, ref=source.ref)
    if isinstance(source, URLSource):
        return GitMarketplaceSource(source="git", url=source.url, ref=source.ref)
    if isinstance(source, HTTPSource):
        return HttpMarketplaceSource(source="http", url=source.url)
    if isinstance(source, GitHubMarketplaceSource):
        return source
    if isinstance(source, GitMarketplaceSource):
        return source
    if isinstance(source, HttpMarketplaceSource):
        return source
    if isinstance(source, DirectoryMarketplaceSource):
        return source
    if isinstance(source, HostPatternMarketplaceSource):
        return source
    raise ValueError(f"Cannot convert source to state format: {type(source)}")


class PluginManager:
    def __init__(
        self,
        marketplace_state: MarketplaceStateAdapter,
        settings: dict[Scope, PluginSettingsAdapter],
        fetcher: FetchAdapter,
    ) -> None:
        self._state = marketplace_state
        self._settings = settings
        self._fetcher = fetcher

    def _settings_for(self, scope: Scope) -> PluginSettingsAdapter:
        adapter = self._settings.get(scope)
        if adapter is None:
            raise ValueError(f"Scope {scope!r} is not configured on this manager")
        return adapter

    def add_marketplace(
        self,
        source: str | object,
        name: str | None = None,
        ref: str | None = None,
    ) -> KnownMarketplaceEntry:
        from ..fetchers._dispatcher import _detect
        from ..models.marketplace import GitHubSource, URLSource

        fetch_source: object = source
        if isinstance(source, str):
            fetch_source = _detect(source)
            if ref is not None:
                if isinstance(fetch_source, GitHubSource):
                    fetch_source = GitHubSource(source="github", repo=fetch_source.repo, ref=ref)
                elif isinstance(fetch_source, URLSource):
                    fetch_source = URLSource(source="url", url=fetch_source.url, ref=ref)

        with self._fetcher.fetch(fetch_source) as path:
            manifest = load_marketplace(path)
            resolved_name = name or manifest.name
            cache_path = self._state.store_cache(resolved_name, path)

        state_source = _source_to_state_source(fetch_source)

        now = datetime.now(timezone.utc)
        entry = KnownMarketplaceEntry(
            source=state_source,
            installLocation=cache_path,
            lastUpdated=now,
        )
        all_marketplaces = self._state.get_marketplaces()
        all_marketplaces[resolved_name] = entry
        self._state.set_marketplaces(all_marketplaces)
        return entry

    def remove_marketplace(self, name: str) -> None:
        all_marketplaces = self._state.get_marketplaces()
        if name not in all_marketplaces:
            raise MarketplaceNotFoundError(name)
        self._state.delete_cache(name)
        del all_marketplaces[name]
        self._state.set_marketplaces(all_marketplaces)

    def list_marketplaces(self) -> dict[str, KnownMarketplaceEntry]:
        return self._state.get_marketplaces()

    def refresh_marketplace(self, name: str) -> MarketplaceManifest:
        all_marketplaces = self._state.get_marketplaces()
        if name not in all_marketplaces:
            raise MarketplaceNotFoundError(name)
        entry = all_marketplaces[name]
        with self._fetcher.fetch(entry.source) as path:
            manifest = load_marketplace(path)
            self._state.store_cache(name, path)
        now = datetime.now(timezone.utc)
        entry = KnownMarketplaceEntry(
            source=entry.source,
            installLocation=self._state.get_cache_path(name),
            lastUpdated=now,
        )
        all_marketplaces[name] = entry
        self._state.set_marketplaces(all_marketplaces)
        return manifest

    def get_marketplace_manifest(self, name: str) -> MarketplaceManifest:
        all_marketplaces = self._state.get_marketplaces()
        if name not in all_marketplaces:
            raise MarketplaceNotFoundError(name)
        return load_marketplace(self._state.get_cache_path(name))

    def install(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        key = _plugin_key(plugin_name, marketplace)
        if self.is_blocked(plugin_name, marketplace):
            raise PluginBlockedError(key)
        all_marketplaces = self._state.get_marketplaces()
        if marketplace not in all_marketplaces:
            raise MarketplaceNotFoundError(marketplace)
        manifest = self.get_marketplace_manifest(marketplace)
        if not any(p.name == plugin_name for p in manifest.plugins):
            raise PluginNotFoundError(plugin_name, marketplace)
        adapter = self._settings_for(scope)
        plugins = adapter.get_enabled_plugins()
        if key in plugins:
            raise AlreadyInstalledError(key)
        plugins[key] = True
        adapter.set_enabled_plugins(plugins)

    def uninstall(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        key = _plugin_key(plugin_name, marketplace)
        adapter = self._settings_for(scope)
        plugins = adapter.get_enabled_plugins()
        if key not in plugins:
            raise NotInstalledError(key)
        del plugins[key]
        adapter.set_enabled_plugins(plugins)

    def enable(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        key = _plugin_key(plugin_name, marketplace)
        adapter = self._settings_for(scope)
        plugins = adapter.get_enabled_plugins()
        if key not in plugins:
            raise NotInstalledError(key)
        plugins[key] = True
        adapter.set_enabled_plugins(plugins)

    def disable(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        key = _plugin_key(plugin_name, marketplace)
        adapter = self._settings_for(scope)
        plugins = adapter.get_enabled_plugins()
        if key not in plugins:
            raise NotInstalledError(key)
        plugins[key] = False
        adapter.set_enabled_plugins(plugins)

    def list_installed(
        self,
        scope: Scope | Literal["all"] = "all",
    ) -> list[InstalledPlugin]:
        result: list[InstalledPlugin] = []
        scopes_to_use: list[Scope] = list(self._settings.keys()) if scope == "all" else [scope]
        for sc in scopes_to_use:
            adapter = self._settings.get(sc)
            if adapter is None:
                continue
            for key, enabled in adapter.get_enabled_plugins().items():
                if "@" not in key:
                    continue
                name, mkt = key.rsplit("@", 1)
                result.append(
                    InstalledPlugin(name=name, marketplace=mkt, enabled=enabled, scope=sc)
                )
        return result

    def is_installed(self, plugin_name: str, marketplace: str) -> bool:
        key = _plugin_key(plugin_name, marketplace)
        return any(key in adapter.get_enabled_plugins() for adapter in self._settings.values())

    def is_enabled(self, plugin_name: str, marketplace: str) -> bool:
        key = _plugin_key(plugin_name, marketplace)
        for adapter in self._settings.values():
            plugins = adapter.get_enabled_plugins()
            if plugins.get(key) is True:
                return True
        return False

    def is_blocked(self, plugin_name: str, marketplace: str) -> bool:
        key = _plugin_key(plugin_name, marketplace)
        return any(entry.plugin == key for entry in self._state.get_blocklist().plugins)

    def get_blocklist(self) -> BlocklistFile:
        return self._state.get_blocklist()

    def check_update(self, plugin_name: str, marketplace: str) -> UpdateCheckResult:
        manifest = self.get_marketplace_manifest(marketplace)
        entry = next((p for p in manifest.plugins if p.name == plugin_name), None)
        if entry is None:
            return UpdateCheckResult(
                plugin_name=plugin_name,
                marketplace=marketplace,
                current_version=None,
                latest_version=None,
                has_update=False,
            )
        latest = entry.version
        current: str | None = None
        for ip in self.list_installed():
            if ip.name == plugin_name and ip.marketplace == marketplace:
                cache_path = self._state.get_cache_path(marketplace)
                plugin_dir = cache_path
                if (cache_path / "plugins" / plugin_name).exists():
                    plugin_dir = cache_path / "plugins" / plugin_name
                elif (cache_path / "external_plugins" / plugin_name).exists():
                    plugin_dir = cache_path / "external_plugins" / plugin_name
                manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
                if manifest_path.exists():
                    import json

                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    current = data.get("version")
                break
        if current is None or latest is None:
            return UpdateCheckResult(
                plugin_name=plugin_name,
                marketplace=marketplace,
                current_version=current,
                latest_version=latest,
                has_update=False,
            )
        has_update = latest != current
        return UpdateCheckResult(
            plugin_name=plugin_name,
            marketplace=marketplace,
            current_version=current,
            latest_version=latest,
            has_update=has_update,
        )

    def check_all_updates(self) -> list[UpdateCheckResult]:
        results: list[UpdateCheckResult] = []
        seen: set[tuple[str, str]] = set()
        for ip in self.list_installed():
            if not ip.enabled:
                continue
            if (ip.name, ip.marketplace) in seen:
                continue
            seen.add((ip.name, ip.marketplace))
            results.append(self.check_update(ip.name, ip.marketplace))
        return results
