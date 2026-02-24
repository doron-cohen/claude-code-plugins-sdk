# Management API — Install, Update, Uninstall

**Goal:** A management API that reads and writes Claude Code plugin state on disk, exposing operations to install, uninstall, enable/disable, check for updates, and manage marketplaces.

**Design:** Domain-driven. `PluginManager` contains pure domain logic and depends on two injected ports — `MarketplaceStateAdapter` and `PluginSettingsAdapter` — plus a `FetchAdapter`. No file paths or HTTP in the manager itself.

**Scope:** Read/write state on disk. No CLI. Phase 1 covers user scope only; the design is scope-aware from day one.

---

## Ground truth: what Claude Code actually stores

```
~/.claude/plugins/
├── known_marketplaces.json    ← marketplace registry
├── blocklist.json             ← blocked plugins (read-only from SDK)
└── marketplaces/
    └── claude-plugins-official/   ← cached marketplace clone
        ├── .claude-plugin/marketplace.json
        └── plugins/

~/.claude/settings.json        ← user-scope plugin state (enabledPlugins)
.claude/settings.json          ← project-scope plugin state
.claude/settings.local.json    ← local-scope plugin state
```

### `known_marketplaces.json`

```json
{
  "claude-plugins-official": {
    "source": {
      "source": "github",
      "repo": "anthropics/claude-plugins-official"
    },
    "installLocation": "/Users/you/.claude/plugins/marketplaces/claude-plugins-official",
    "lastUpdated": "2026-02-23T09:13:59.983Z"
  }
}
```

### `blocklist.json`

```json
{
  "fetchedAt": "2026-02-23T09:12:03.866Z",
  "plugins": [
    {
      "plugin": "code-review@claude-plugins-official",
      "added_at": "2026-02-11T03:16:31.424Z",
      "reason": "security",
      "text": "Human-readable description"
    }
  ]
}
```

### `settings.json` (plugin-relevant slice)

```json
{
  "enabledPlugins": {
    "formatter@acme-tools": true,
    "deployer@acme-tools": true,
    "analyzer@security-plugins": false
  },
  "extraKnownMarketplaces": {
    "acme-tools": {
      "source": { "source": "github", "repo": "acme-corp/claude-plugins" }
    }
  }
}
```

`enabledPlugins` format: `"plugin-name@marketplace-name": true/false`
- `true` = installed and enabled
- `false` = installed but disabled

---

## Architecture

Three ports, two concrete adapters, one manager.

```
                    ┌─────────────────────────────┐
                    │        PluginManager         │
                    │   (pure domain logic only)   │
                    └──────┬──────────┬────────────┘
                           │          │
          ┌────────────────┘          └────────────────────┐
          ▼                                                 ▼
┌──────────────────────┐                     ┌─────────────────────────┐
│ MarketplaceState     │                     │  PluginSettings         │
│ Adapter (port)       │                     │  Adapter (port)         │
│                      │                     │                         │
│ get_marketplaces()   │                     │  get_enabled_plugins()  │
│ set_marketplaces()   │                     │  set_enabled_plugins()  │
│ get_blocklist()      │                     └─────────────────────────┘
│ get_cache_path()     │                              ▲
│ store_cache()        │                              │
│ delete_cache()       │              ┌───────────────┴──────────────┐
└──────────────────────┘              │  one adapter per scope       │
          ▲                           │  {"user": ..., "project": ...}
          │                           └──────────────────────────────┘
┌──────────────────────┐
│ LocalFilesystem      │                     ┌─────────────────────────┐
│ MarketplaceAdapter   │                     │  LocalFilesystem        │
│                      │                     │  SettingsAdapter        │
│ reads/writes         │                     │                         │
│ ~/.claude/plugins/   │                     │  reads/writes one       │
└──────────────────────┘                     │  settings.json file     │
                                             └─────────────────────────┘

                    ┌─────────────────────────────┐
                    │        FetchAdapter          │
                    │                             │
                    │  fetch(source) -> Path      │
                    └─────────────────────────────┘
                                  ▲
                    ┌─────────────┴─────────────┐
                    │   DefaultFetchAdapter      │
                    │                           │
                    │  dispatches to existing   │
                    │  git / github / http /    │
                    │  local fetchers           │
                    └───────────────────────────┘
```

---

## Ports

### `MarketplaceStateAdapter`

Manages `~/.claude/plugins/` — the marketplace registry and file cache.

```python
class MarketplaceStateAdapter(Protocol):
    def get_marketplaces(self) -> dict[str, KnownMarketplaceEntry]: ...
    def set_marketplaces(self, data: dict[str, KnownMarketplaceEntry]) -> None: ...

    def get_blocklist(self) -> BlocklistFile: ...
    # blocklist is read-only — Claude Code writes it, SDK only reads it

    def get_cache_path(self, name: str) -> Path: ...
    def store_cache(self, name: str, source_path: Path) -> Path: ...
    def delete_cache(self, name: str) -> None: ...
```

### `PluginSettingsAdapter`

Manages `enabledPlugins` in a single `settings.json`. One instance per scope.

```python
class PluginSettingsAdapter(Protocol):
    def get_enabled_plugins(self) -> dict[str, bool]: ...
    def set_enabled_plugins(self, data: dict[str, bool]) -> None: ...
    # set_enabled_plugins must merge — preserve all other keys in settings.json
```

### `FetchAdapter`

Resolves any source string or structured source object to a local path.

```python
class FetchAdapter(Protocol):
    def fetch(self, source: str | AnyMarketplaceSource) -> Path:
        """
        Fetch the source into a temp directory and return the path.
        Caller is responsible for cleanup (or use as context manager).
        """
        ...
```

---

## `PluginManager`

Pure domain logic. No file I/O, no HTTP.

```python
Scope = Literal["user", "project", "local"]

class PluginManager:
    def __init__(
        self,
        marketplace_state: MarketplaceStateAdapter,
        settings: dict[Scope, PluginSettingsAdapter],
        fetcher: FetchAdapter,
    ): ...

    # --- Marketplace management ---

    def add_marketplace(
        self,
        source: str | AnyMarketplaceSource,
        name: str | None = None,
        ref: str | None = None,
    ) -> KnownMarketplaceEntry:
        """
        Fetch the marketplace, cache it, register in known_marketplaces.json.
        name defaults to the marketplace's own `name` field from its manifest.
        """

    def remove_marketplace(self, name: str) -> None:
        """Unregister and delete the cached files."""

    def list_marketplaces(self) -> dict[str, KnownMarketplaceEntry]:
        """Return all known marketplaces."""

    def refresh_marketplace(self, name: str) -> MarketplaceManifest:
        """Re-fetch and update the cache + lastUpdated timestamp."""

    def get_marketplace_manifest(self, name: str) -> MarketplaceManifest:
        """Load the cached manifest for a known marketplace."""

    # --- Plugin management ---

    def install(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        """
        Add "plugin@marketplace": true to the target scope's enabledPlugins.

        Raises:
            MarketplaceNotFoundError  — marketplace not in known_marketplaces
            PluginNotFoundError       — plugin not in the marketplace manifest
            PluginBlockedError        — plugin is on the blocklist
            AlreadyInstalledError     — already present (true or false) in this scope
            ValueError                — scope not configured on this manager
        """

    def uninstall(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        """Remove the key from enabledPlugins in the target scope."""

    def enable(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        """Set "plugin@marketplace": true in the target scope."""

    def disable(
        self,
        plugin_name: str,
        marketplace: str,
        scope: Scope = "user",
    ) -> None:
        """Set "plugin@marketplace": false in the target scope."""

    def list_installed(
        self,
        scope: Scope | Literal["all"] = "all",
    ) -> list[InstalledPlugin]:
        """
        Return all plugins from enabledPlugins across requested scopes.
        When scope="all", iterates all configured scope adapters.
        """

    def is_installed(self, plugin_name: str, marketplace: str) -> bool:
        """True if the key exists in any configured scope (any value)."""

    def is_enabled(self, plugin_name: str, marketplace: str) -> bool:
        """True if the key is set to true in any configured scope."""

    # --- Blocklist ---

    def is_blocked(self, plugin_name: str, marketplace: str) -> bool:
        """Check blocklist.json via the marketplace_state adapter."""

    def get_blocklist(self) -> BlocklistFile:
        """Return the full blocklist."""

    # --- Update checking ---

    def check_update(
        self,
        plugin_name: str,
        marketplace: str,
    ) -> UpdateCheckResult:
        """
        Compare the installed plugin's version against the cached marketplace entry.
        Requires the marketplace to be in known_marketplaces (cached locally).
        """

    def check_all_updates(self) -> list[UpdateCheckResult]:
        """check_update for every installed+enabled plugin across all scopes."""
```

---

## Concrete adapters

### `LocalFilesystemMarketplaceAdapter`

```python
class LocalFilesystemMarketplaceAdapter:
    def __init__(self, plugins_dir: Path):
        # plugins_dir defaults to ~/.claude/plugins
        self._dir = plugins_dir
        self._marketplaces_file = plugins_dir / "known_marketplaces.json"
        self._blocklist_file = plugins_dir / "blocklist.json"
        self._cache_dir = plugins_dir / "marketplaces"
```

Writes are atomic: write to `.tmp` then `os.replace()`. Missing files return empty state.

### `LocalFilesystemSettingsAdapter`

```python
class LocalFilesystemSettingsAdapter:
    def __init__(self, settings_path: Path):
        self._path = settings_path

    def get_enabled_plugins(self) -> dict[str, bool]:
        # read settings.json, return enabledPlugins or {}

    def set_enabled_plugins(self, data: dict[str, bool]) -> None:
        # read full settings.json, merge enabledPlugins key, write back atomically
        # preserves all other keys
```

### `DefaultFetchAdapter`

```python
class DefaultFetchAdapter:
    def fetch(self, source: str | AnyMarketplaceSource) -> Path:
        # wraps existing fetchers/_dispatcher.py logic
        # returns a temp directory path
```

### `InMemoryMarketplaceAdapter` (for tests)

```python
class InMemoryMarketplaceAdapter:
    def __init__(
        self,
        marketplaces: dict[str, KnownMarketplaceEntry] | None = None,
        blocklist: BlocklistFile | None = None,
    ): ...
```

### `InMemorySettingsAdapter` (for tests)

```python
class InMemorySettingsAdapter:
    def __init__(self, enabled_plugins: dict[str, bool] | None = None): ...
```

---

## Convenience factory

```python
def make_plugin_manager(
    plugins_dir: Path | None = None,
    user_settings: Path | None = None,
    project_root: Path | None = None,
) -> PluginManager:
    """
    Build a PluginManager wired to the local filesystem.

    plugins_dir     defaults to ~/.claude/plugins
    user_settings   defaults to ~/.claude/settings.json
    project_root    if provided, also wires project + local scope adapters
    """
    plugins_dir = plugins_dir or Path.home() / ".claude" / "plugins"
    user_settings = user_settings or Path.home() / ".claude" / "settings.json"

    scopes: dict[Scope, PluginSettingsAdapter] = {
        "user": LocalFilesystemSettingsAdapter(user_settings),
    }
    if project_root:
        scopes["project"] = LocalFilesystemSettingsAdapter(
            project_root / ".claude" / "settings.json"
        )
        scopes["local"] = LocalFilesystemSettingsAdapter(
            project_root / ".claude" / "settings.local.json"
        )

    return PluginManager(
        marketplace_state=LocalFilesystemMarketplaceAdapter(plugins_dir),
        settings=scopes,
        fetcher=DefaultFetchAdapter(),
    )
```

---

## Models

### `models/state.py`

```python
class GitHubMarketplaceSource(BaseModel):
    source: Literal["github"]
    repo: str
    ref: str | None = None

class GitMarketplaceSource(BaseModel):
    source: Literal["git"]
    url: str
    ref: str | None = None

class DirectoryMarketplaceSource(BaseModel):
    source: Literal["directory"]
    path: str

class HostPatternMarketplaceSource(BaseModel):
    source: Literal["hostPattern"]
    host_pattern: str = Field(alias="hostPattern")

AnyMarketplaceSource = Annotated[
    GitHubMarketplaceSource | GitMarketplaceSource |
    DirectoryMarketplaceSource | HostPatternMarketplaceSource,
    Field(discriminator="source"),
]

class KnownMarketplaceEntry(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: AnyMarketplaceSource
    install_location: Path = Field(alias="installLocation")
    last_updated: datetime = Field(alias="lastUpdated")

class BlocklistPlugin(BaseModel):
    plugin: str           # "name@marketplace"
    added_at: datetime
    reason: str | None = None
    text: str | None = None

class BlocklistFile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fetched_at: datetime = Field(alias="fetchedAt")
    plugins: list[BlocklistPlugin] = []
```

### Supporting types (in `manager/`)

```python
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
```

---

## Errors

```python
class AlreadyInstalledError(Exception):
    def __init__(self, key: str): ...

class NotInstalledError(Exception):
    def __init__(self, key: str): ...

class MarketplaceNotFoundError(Exception):
    def __init__(self, name: str): ...

class PluginNotFoundError(Exception):
    def __init__(self, name: str, marketplace: str): ...

class PluginBlockedError(Exception):
    def __init__(self, key: str, reason: str | None = None): ...
```

---

## Package layout

```
src/claude_code_plugins_sdk/
├── manager/
│   ├── __init__.py          ← PluginManager, make_plugin_manager,
│   │                           InstalledPlugin, UpdateCheckResult, Scope
│   ├── _manager.py          ← PluginManager
│   ├── _adapters.py         ← LocalFilesystemMarketplaceAdapter,
│   │                           LocalFilesystemSettingsAdapter,
│   │                           DefaultFetchAdapter
│   ├── _in_memory.py        ← InMemoryMarketplaceAdapter,
│   │                           InMemorySettingsAdapter (test helpers)
│   └── _protocols.py        ← MarketplaceStateAdapter, PluginSettingsAdapter,
│                               FetchAdapter (Protocol classes)
└── models/
    └── state.py             ← KnownMarketplaceEntry, BlocklistFile, BlocklistPlugin,
                                AnyMarketplaceSource, and source subtypes
```

---

## What we need from existing code

| Need | Status |
|---|---|
| `fetch_marketplace(source)` → fetches + parses a marketplace | ✅ exists |
| `load_marketplace(path)` → loads from disk | ✅ exists |
| `load_plugin(path)` | ✅ exists |
| `validate_plugin(data)` | ✅ exists |
| Source type detection / dispatching | ✅ `fetchers/_dispatcher.py` |
| `models/state.py` | ❌ needs building |
| `_protocols.py` | ❌ needs building |
| `_adapters.py` (filesystem) | ❌ needs building |
| `_in_memory.py` (test helpers) | ❌ needs building |
| `_manager.py` | ❌ needs building |

---

## Phase 2 notes

The design is already scope-aware. Phase 2 just means:
- passing `project_root` to `make_plugin_manager`
- wiring `project` and `local` scope adapters
- the manager code itself doesn't change

`extraKnownMarketplaces` in project `settings.json` is a related concept (team-declared marketplaces). Phase 2 can add `PluginSettingsAdapter.get_extra_marketplaces()` to read that field and merge it into `list_marketplaces()`.

---

## Tests

All tests inject in-memory adapters — no disk I/O, no HTTP.

```python
def make_test_manager(
    marketplaces=None,
    blocklist=None,
    user_plugins=None,
) -> PluginManager:
    return PluginManager(
        marketplace_state=InMemoryMarketplaceAdapter(marketplaces, blocklist),
        settings={"user": InMemorySettingsAdapter(user_plugins)},
        fetcher=MockFetchAdapter(),
    )
```

`test_manager_marketplaces.py`:
- `add_marketplace` → appears in `list_marketplaces()`
- `remove_marketplace` → gone, cache deleted
- `remove_marketplace` unknown → `MarketplaceNotFoundError`
- `get_marketplace_manifest` → returns parsed manifest

`test_manager_install.py`:
- `install` → `"plugin@marketplace": true` in settings
- install blocked plugin → `PluginBlockedError`
- install unknown marketplace → `MarketplaceNotFoundError`
- install unknown plugin → `PluginNotFoundError`
- install already installed → `AlreadyInstalledError`
- `disable` → entry becomes `false`
- `enable` → entry becomes `true`
- `uninstall` → key removed
- `list_installed()` → correct `InstalledPlugin` list
- `is_installed` / `is_enabled` → correct booleans

`test_manager_updates.py`:
- versions match → `has_update=False`
- marketplace has newer version → `has_update=True`
- no version on either side → `has_update=False`

`test_filesystem_adapters.py`:
- round-trip `known_marketplaces.json`: save + load → same data
- `set_enabled_plugins` merges, preserves unrelated settings.json keys
- atomic write: `.tmp` cleaned up, no partial state on failure
- missing file → empty state (not an error)

---

## Done when

- [ ] `models/state.py` parses real `known_marketplaces.json` and `blocklist.json`
- [ ] `_protocols.py` defines the three Protocol classes
- [ ] `_adapters.py` filesystem adapters pass `test_filesystem_adapters.py`
- [ ] `_in_memory.py` test helpers exist
- [ ] `PluginManager` passes all manager tests using in-memory adapters
- [ ] `make_plugin_manager()` factory wires everything for the default case
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src/ tests/` exits 0
