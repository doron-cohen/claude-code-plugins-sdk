"""Concrete adapters for local filesystem and default fetch."""

from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..errors import FetchError
from ..models.marketplace import GitHubSource, HTTPSource, URLSource
from ..models.state import BlocklistFile, KnownMarketplaceEntry


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def _load_json(path: Path, default: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


class LocalFilesystemMarketplaceAdapter:
    """Reads/writes ~/.claude/plugins/ (known_marketplaces.json, blocklist, marketplaces cache)."""

    def __init__(self, plugins_dir: Path) -> None:
        self._dir = Path(plugins_dir)
        self._marketplaces_file = self._dir / "known_marketplaces.json"
        self._blocklist_file = self._dir / "blocklist.json"
        self._cache_dir = self._dir / "marketplaces"
        self._plugin_cache_dir = self._dir / "plugin-cache"

    def get_marketplaces(self) -> dict[str, KnownMarketplaceEntry]:
        raw = _load_json(self._marketplaces_file, {})
        if not isinstance(raw, dict):
            return {}
        return {
            k: KnownMarketplaceEntry.model_validate(v)
            for k, v in raw.items()
            if isinstance(v, dict)
        }

    def set_marketplaces(self, data: dict[str, KnownMarketplaceEntry]) -> None:
        out = {k: v.model_dump(by_alias=True, exclude_none=False) for k, v in data.items()}
        for v in out.values():
            if "installLocation" in v:
                v["installLocation"] = str(v["installLocation"])
            if "lastUpdated" in v and hasattr(v["lastUpdated"], "isoformat"):
                v["lastUpdated"] = v["lastUpdated"].isoformat()
        _atomic_write(self._marketplaces_file, json.dumps(out, indent=2))

    def get_blocklist(self) -> BlocklistFile:
        raw = _load_json(self._blocklist_file, {"fetchedAt": "1970-01-01T00:00:00Z", "plugins": []})
        if not isinstance(raw, dict):
            return _default_blocklist()
        try:
            return BlocklistFile.model_validate(raw)
        except Exception:
            return _default_blocklist()

    def get_cache_path(self, name: str) -> Path:
        return self._cache_dir / name

    def store_cache(self, name: str, source_path: Path) -> Path:
        dest = self._cache_dir / name
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_path, dest)
        return dest

    def delete_cache(self, name: str) -> None:
        dest = self._cache_dir / name
        if dest.exists() and dest.is_dir():
            shutil.rmtree(dest)

    def store_plugin_cache(self, marketplace: str, plugin_name: str, source_path: Path) -> Path:
        dest = self._plugin_cache_dir / marketplace / plugin_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_path, dest)
        return dest

    def get_plugin_cache_path(self, marketplace: str, plugin_name: str) -> Path:
        return self._plugin_cache_dir / marketplace / plugin_name

    def delete_plugin_cache(self, marketplace: str, plugin_name: str) -> None:
        dest = self._plugin_cache_dir / marketplace / plugin_name
        if dest.exists() and dest.is_dir():
            shutil.rmtree(dest)


class LocalFilesystemSettingsAdapter:
    """Reads/writes enabledPlugins in a single settings.json, preserving other keys."""

    def __init__(self, settings_path: Path) -> None:
        self._path = Path(settings_path)

    def get_enabled_plugins(self) -> dict[str, bool]:
        raw = _load_json(self._path, {})
        if not isinstance(raw, dict):
            return {}
        plugins = raw.get("enabledPlugins")
        if not isinstance(plugins, dict):
            return {}
        return {k: bool(v) for k, v in plugins.items()}

    def set_enabled_plugins(self, data: dict[str, bool]) -> None:
        raw = _load_json(self._path, {})
        if not isinstance(raw, dict):
            raw = {}
        raw["enabledPlugins"] = data
        _atomic_write(self._path, json.dumps(raw, indent=2))


def _default_blocklist() -> BlocklistFile:
    return BlocklistFile(fetchedAt=datetime(1970, 1, 1, tzinfo=timezone.utc), plugins=[])


def _detect_source(s: str) -> GitHubSource | URLSource | HTTPSource:
    from ..fetchers._dispatcher import _detect

    return _detect(s)


@contextmanager
def _fetch_git(url: str, ref: str | None):
    from ..fetchers._git import _clone

    with tempfile.TemporaryDirectory() as tmpdir:
        _clone(url, Path(tmpdir), ref=ref)
        yield Path(tmpdir)


@contextmanager
def _fetch_http(url: str):
    from ..fetchers._http import fetch_via_http

    manifest = fetch_via_http(url)
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / ".claude-plugin").mkdir()
        (p / ".claude-plugin" / "marketplace.json").write_text(
            manifest.model_dump_json(by_alias=True, exclude_none=False),
            encoding="utf-8",
        )
        yield p


class DefaultFetchAdapter:
    """Fetches marketplace via git, HTTP, or local path. Yields a path; temp dirs cleaned on exit."""

    def fetch(self, source: str | object):
        if isinstance(source, str):
            if source.startswith((".", "/")):
                resolved = Path(source).resolve()
                if not resolved.is_dir():
                    raise FetchError(f"Not a directory: {resolved}", url=source)
                return _context_yield_only(resolved)
            source = _detect_source(source)

        if isinstance(source, GitHubSource):
            url = f"https://github.com/{source.repo}.git"
            return _fetch_git(url, source.ref)
        if isinstance(source, URLSource):
            return _fetch_git(source.url, source.ref)
        if isinstance(source, HTTPSource):
            return _fetch_http(source.url)

        from ..models.state import (
            DirectoryMarketplaceSource,
            GitHubMarketplaceSource,
            GitMarketplaceSource,
            HostPatternMarketplaceSource,
            HttpMarketplaceSource,
        )

        if isinstance(source, GitHubMarketplaceSource):
            url = f"https://github.com/{source.repo}.git"
            return _fetch_git(url, source.ref)
        if isinstance(source, GitMarketplaceSource):
            return _fetch_git(source.url, source.ref)
        if isinstance(source, HttpMarketplaceSource):
            return _fetch_http(source.url)
        if isinstance(source, DirectoryMarketplaceSource):
            resolved = Path(source.path).resolve()
            if not resolved.is_dir():
                raise FetchError(f"Not a directory: {resolved}", url=source.path)
            return _context_yield_only(resolved)
        if isinstance(source, HostPatternMarketplaceSource):
            raise FetchError("hostPattern source cannot be fetched to a path", url="")
        raise FetchError(f"Unsupported source type: {type(source)}")


@contextmanager
def _context_yield_only(path: Path):
    """Context manager that yields path and does nothing on exit (no cleanup)."""
    yield path
