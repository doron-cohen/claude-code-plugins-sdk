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
