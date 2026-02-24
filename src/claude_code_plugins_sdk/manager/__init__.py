"""Plugin management API — install, uninstall, marketplaces, updates."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from ._adapters import (
    DefaultFetchAdapter,
    LocalFilesystemMarketplaceAdapter,
    LocalFilesystemSettingsAdapter,
)
from ._manager import (
    InstalledPlugin,
    PluginManager,
    Scope,
    UpdateCheckResult,
)
from ._protocols import PluginSettingsAdapter


def make_plugin_manager(
    plugins_dir: Path | None = None,
    user_settings: Path | None = None,
    project_root: Path | None = None,
) -> PluginManager:
    """Build a PluginManager with local filesystem adapters.

    plugins_dir: defaults to ~/.claude/plugins
    user_settings: defaults to ~/.claude/settings.json
    project_root: if set, also wires project and local scope adapters
    """
    home = Path.home()
    plugins_dir = plugins_dir or home / ".claude" / "plugins"
    user_settings = user_settings or home / ".claude" / "settings.json"

    settings: dict[Scope, LocalFilesystemSettingsAdapter] = {
        "user": LocalFilesystemSettingsAdapter(user_settings),
    }
    if project_root is not None:
        project_root = Path(project_root)
        settings["project"] = LocalFilesystemSettingsAdapter(
            project_root / ".claude" / "settings.json"
        )
        settings["local"] = LocalFilesystemSettingsAdapter(
            project_root / ".claude" / "settings.local.json"
        )

    return PluginManager(
        marketplace_state=LocalFilesystemMarketplaceAdapter(plugins_dir),
        settings=cast("dict[Scope, PluginSettingsAdapter]", settings),
        fetcher=DefaultFetchAdapter(),
    )


__all__ = [
    "DefaultFetchAdapter",
    "InstalledPlugin",
    "LocalFilesystemMarketplaceAdapter",
    "LocalFilesystemSettingsAdapter",
    "PluginManager",
    "Scope",
    "UpdateCheckResult",
    "make_plugin_manager",
]
