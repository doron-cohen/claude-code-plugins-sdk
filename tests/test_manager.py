"""Tests for PluginManager and adapters."""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_code_plugins_sdk import (
    AlreadyInstalledError,
    MarketplaceNotFoundError,
    NotInstalledError,
    PluginBlockedError,
    PluginManager,
    PluginNotFoundError,
)
from claude_code_plugins_sdk.errors import FetchError
from claude_code_plugins_sdk.manager._in_memory import (
    InMemoryMarketplaceAdapter,
    InMemorySettingsAdapter,
)
from claude_code_plugins_sdk.models.state import (
    BlocklistFile,
    BlocklistPlugin,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "marketplace"


@contextmanager
def _yield_fixture_path():
    yield FIXTURES


class MockFetchAdapter:
    """Yields the fixture marketplace path for any source."""

    def fetch(self, source):
        return _yield_fixture_path()


class CountingFetchAdapter:
    """Tracks fetch calls and yields the fixture marketplace path."""

    def __init__(self):
        self.call_count = 0

    def fetch(self, source):
        self.call_count += 1
        return _yield_fixture_path()


def _make_manager(
    marketplaces=None,
    blocklist=None,
    user_plugins=None,
    fetcher=None,
):
    return PluginManager(
        marketplace_state=InMemoryMarketplaceAdapter(marketplaces, blocklist),
        settings={"user": InMemorySettingsAdapter(user_plugins)},
        fetcher=fetcher or MockFetchAdapter(),
    )


def test_add_marketplace_appears_in_list():
    manager = _make_manager()
    entry = manager.add_marketplace("owner/repo")
    assert entry.source.repo == "owner/repo"
    listed = manager.list_marketplaces()
    assert "example-marketplace" in listed
    assert listed["example-marketplace"].source.repo == "owner/repo"


def test_remove_marketplace():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.remove_marketplace("example-marketplace")
    assert manager.list_marketplaces() == {}


def test_remove_marketplace_unknown_raises():
    manager = _make_manager()
    with pytest.raises(MarketplaceNotFoundError, match="no-such"):
        manager.remove_marketplace("no-such")


def test_get_marketplace_manifest():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manifest = manager.get_marketplace_manifest("example-marketplace")
    assert manifest.name == "example-marketplace"
    assert len(manifest.plugins) >= 1
    names = [p.name for p in manifest.plugins]
    assert "local-plugin" in names


def test_get_marketplace_manifest_unknown_raises():
    manager = _make_manager()
    with pytest.raises(MarketplaceNotFoundError, match="no-such"):
        manager.get_marketplace_manifest("no-such")


def test_install_adds_to_enabled_plugins():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.install("local-plugin", "example-marketplace")
    installed = manager.list_installed()
    assert len(installed) == 1
    assert installed[0].name == "local-plugin"
    assert installed[0].marketplace == "example-marketplace"
    assert installed[0].enabled is True


def test_install_blocked_plugin_raises():
    ts = datetime(1970, 1, 1, tzinfo=timezone.utc)
    blocklist = BlocklistFile(
        fetchedAt=ts,
        plugins=[BlocklistPlugin(plugin="local-plugin@example-marketplace", added_at=ts)],
    )
    manager = _make_manager(blocklist=blocklist)
    manager.add_marketplace("owner/repo")
    with pytest.raises(PluginBlockedError, match="local-plugin@example-marketplace"):
        manager.install("local-plugin", "example-marketplace")


def test_install_unknown_marketplace_raises():
    manager = _make_manager()
    with pytest.raises(MarketplaceNotFoundError, match="no-such"):
        manager.install("local-plugin", "no-such")


def test_install_unknown_plugin_raises():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    with pytest.raises(PluginNotFoundError, match="nonexistent-plugin.*example-marketplace"):
        manager.install("nonexistent-plugin", "example-marketplace")


def test_install_already_installed_raises():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.install("local-plugin", "example-marketplace")
    with pytest.raises(AlreadyInstalledError, match="local-plugin@example-marketplace"):
        manager.install("local-plugin", "example-marketplace")


def test_disable_and_enable():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.install("local-plugin", "example-marketplace")
    manager.disable("local-plugin", "example-marketplace")
    installed = manager.list_installed()
    assert installed[0].enabled is False
    manager.enable("local-plugin", "example-marketplace")
    installed = manager.list_installed()
    assert installed[0].enabled is True


def test_uninstall_removes_from_list():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.install("local-plugin", "example-marketplace")
    manager.uninstall("local-plugin", "example-marketplace")
    assert manager.list_installed() == []


def test_uninstall_not_installed_raises():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    with pytest.raises(NotInstalledError, match="local-plugin@example-marketplace"):
        manager.uninstall("local-plugin", "example-marketplace")


def test_is_installed_and_is_enabled():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    assert manager.is_installed("local-plugin", "example-marketplace") is False
    manager.install("local-plugin", "example-marketplace")
    assert manager.is_installed("local-plugin", "example-marketplace") is True
    assert manager.is_enabled("local-plugin", "example-marketplace") is True
    manager.disable("local-plugin", "example-marketplace")
    assert manager.is_installed("local-plugin", "example-marketplace") is True
    assert manager.is_enabled("local-plugin", "example-marketplace") is False


def test_is_blocked():
    from datetime import datetime, timezone

    blocklist = BlocklistFile(
        fetchedAt=datetime(1970, 1, 1, tzinfo=timezone.utc),
        plugins=[BlocklistPlugin(plugin="a@b", added_at=datetime(1970, 1, 1, tzinfo=timezone.utc))],
    )
    manager = _make_manager(blocklist=blocklist)
    assert manager.is_blocked("a", "b") is True
    assert manager.is_blocked("a", "c") is False


def test_check_update_no_version_has_update_false():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.install("local-plugin", "example-marketplace")
    result = manager.check_update("local-plugin", "example-marketplace")
    assert result.plugin_name == "local-plugin"
    assert result.marketplace == "example-marketplace"
    assert result.has_update is False


def test_scope_not_configured_raises():
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    with pytest.raises(ValueError, match="project"):
        manager.install("local-plugin", "example-marketplace", scope="project")


# --- plugin-cache tests ---


def test_install_external_source_fetches_plugin_files():
    """Installing a GitHub-sourced plugin should populate the plugin cache."""
    fetcher = CountingFetchAdapter()
    manager = _make_manager(fetcher=fetcher)
    manager.add_marketplace("owner/repo")  # call 1
    manager.install("github-plugin", "example-marketplace")  # call 2

    # Fetch was called for the plugin (beyond the marketplace fetch)
    assert fetcher.call_count == 2

    # Plugin cache dir should exist and be a directory
    cache_path = manager._state.get_plugin_cache_path("example-marketplace", "github-plugin")
    assert cache_path.is_dir()

    # It should contain the files copied from FIXTURES
    assert (cache_path / ".claude-plugin").is_dir()


def test_install_relative_source_no_fetch():
    """Installing a string-source plugin must not trigger an extra fetch."""
    fetcher = CountingFetchAdapter()
    manager = _make_manager(fetcher=fetcher)
    manager.add_marketplace("owner/repo")  # call 1
    fetcher.call_count = 0  # reset after marketplace fetch
    manager.install("local-plugin", "example-marketplace")

    # No additional fetch should occur for a relative-path source
    assert fetcher.call_count == 0

    # Plugin cache should NOT be populated
    cache_path = manager._state.get_plugin_cache_path("example-marketplace", "local-plugin")
    assert not cache_path.is_dir()


def test_install_npm_source_raises_fetch_error():
    """Installing a plugin with NPMSource must raise FetchError."""
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    with pytest.raises(FetchError, match="NPMSource"):
        manager.install("npm-plugin", "example-marketplace")


def test_install_pip_source_raises_fetch_error():
    """Installing a plugin with PIPSource must raise FetchError."""
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    with pytest.raises(FetchError, match="PIPSource"):
        manager.install("pip-plugin", "example-marketplace")


def test_uninstall_clears_plugin_cache():
    """Uninstalling an external plugin should remove its plugin cache."""
    manager = _make_manager()
    manager.add_marketplace("owner/repo")
    manager.install("github-plugin", "example-marketplace")

    cache_path = manager._state.get_plugin_cache_path("example-marketplace", "github-plugin")
    assert cache_path.is_dir()

    manager.uninstall("github-plugin", "example-marketplace")
    assert not cache_path.is_dir()


def test_uninstall_keeps_cache_when_installed_in_other_scope():
    """Cache should survive uninstall when plugin remains installed in another scope."""
    state = InMemoryMarketplaceAdapter()
    manager = PluginManager(
        marketplace_state=state,
        settings={
            "user": InMemorySettingsAdapter(),
            "project": InMemorySettingsAdapter(),
        },
        fetcher=MockFetchAdapter(),
    )
    manager.add_marketplace("owner/repo")
    manager.install("github-plugin", "example-marketplace", scope="user")
    manager.install("github-plugin", "example-marketplace", scope="project")

    cache_path = state.get_plugin_cache_path("example-marketplace", "github-plugin")
    assert cache_path.is_dir()

    # Uninstall from user scope — still installed in project scope
    manager.uninstall("github-plugin", "example-marketplace", scope="user")
    assert cache_path.is_dir()

    # Uninstall from project scope — now fully gone
    manager.uninstall("github-plugin", "example-marketplace", scope="project")
    assert not cache_path.is_dir()
