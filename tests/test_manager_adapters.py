"""Tests for filesystem adapters (state store round-trip, merge)."""

import json
from datetime import datetime, timezone

from claude_code_plugins_sdk.manager._adapters import (
    LocalFilesystemMarketplaceAdapter,
    LocalFilesystemSettingsAdapter,
)
from claude_code_plugins_sdk.models.state import (
    GitHubMarketplaceSource,
    KnownMarketplaceEntry,
)


def test_marketplace_adapter_round_trip(tmp_path):
    adapter = LocalFilesystemMarketplaceAdapter(tmp_path)
    assert adapter.get_marketplaces() == {}

    entry = KnownMarketplaceEntry(
        source=GitHubMarketplaceSource(source="github", repo="owner/repo"),
        installLocation=tmp_path / "marketplaces" / "test",
        lastUpdated=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    adapter.set_marketplaces({"test-mkt": entry})
    loaded = adapter.get_marketplaces()
    assert "test-mkt" in loaded
    src = loaded["test-mkt"].source
    assert isinstance(src, GitHubMarketplaceSource) and src.repo == "owner/repo"


def test_marketplace_adapter_missing_file_returns_empty(tmp_path):
    adapter = LocalFilesystemMarketplaceAdapter(tmp_path)
    assert adapter.get_marketplaces() == {}


def test_settings_adapter_round_trip(tmp_path):
    settings_path = tmp_path / "settings.json"
    adapter = LocalFilesystemSettingsAdapter(settings_path)
    assert adapter.get_enabled_plugins() == {}

    adapter.set_enabled_plugins({"a@b": True, "c@d": False})
    assert adapter.get_enabled_plugins() == {"a@b": True, "c@d": False}


def test_settings_adapter_merge_preserves_other_keys(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"model": "opus", "enabledPlugins": {"old@m": True}}))
    adapter = LocalFilesystemSettingsAdapter(settings_path)
    plugins = adapter.get_enabled_plugins()
    plugins["new@m"] = True
    adapter.set_enabled_plugins(plugins)

    data = json.loads(settings_path.read_text())
    assert data["model"] == "opus"
    assert data["enabledPlugins"]["old@m"] is True
    assert data["enabledPlugins"]["new@m"] is True


def test_settings_adapter_missing_file_returns_empty(tmp_path):
    adapter = LocalFilesystemSettingsAdapter(tmp_path / "nonexistent.json")
    assert adapter.get_enabled_plugins() == {}


# --- plugin cache tests ---


def test_store_and_get_plugin_cache(tmp_path):
    adapter = LocalFilesystemMarketplaceAdapter(tmp_path)

    source = tmp_path / "source-plugin"
    source.mkdir()
    (source / "HELLO.txt").write_text("hi")

    result = adapter.store_plugin_cache("my-marketplace", "my-plugin", source)
    assert result.is_dir()
    assert (result / "HELLO.txt").read_text() == "hi"

    fetched = adapter.get_plugin_cache_path("my-marketplace", "my-plugin")
    assert fetched == result
    assert (fetched / "HELLO.txt").read_text() == "hi"


def test_delete_plugin_cache(tmp_path):
    adapter = LocalFilesystemMarketplaceAdapter(tmp_path)

    source = tmp_path / "source-plugin"
    source.mkdir()
    (source / "file.txt").write_text("data")

    adapter.store_plugin_cache("mkt", "plugin", source)
    cache_path = adapter.get_plugin_cache_path("mkt", "plugin")
    assert cache_path.is_dir()

    adapter.delete_plugin_cache("mkt", "plugin")
    assert not cache_path.exists()


def test_delete_plugin_cache_noop_if_missing(tmp_path):
    adapter = LocalFilesystemMarketplaceAdapter(tmp_path)
    # Should not raise even if nothing was ever stored
    adapter.delete_plugin_cache("mkt", "no-such-plugin")


def test_get_plugin_cache_path_not_yet_fetched(tmp_path):
    adapter = LocalFilesystemMarketplaceAdapter(tmp_path)
    path = adapter.get_plugin_cache_path("mkt", "plugin")
    # Returns a path — no exception — but it doesn't exist yet
    assert not path.exists()
    assert path.name == "plugin"
