from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .plugin import Author  # noqa: TC001


class GitHubSource(BaseModel):
    """Fetch a marketplace by cloning a GitHub repository."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["github"]
    repo: str  # "owner/repo" format
    ref: str | None = None  # branch or tag
    sha: str | None = None  # full 40-char commit SHA


class URLSource(BaseModel):
    """Fetch a marketplace by cloning a git URL (must end with .git)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["url"]
    url: str
    ref: str | None = None
    sha: str | None = None


class NPMSource(BaseModel):
    """Plugin source via npm package (not yet fully implemented)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["npm"]
    package: str
    version: str | None = None
    registry: str | None = None


class PIPSource(BaseModel):
    """Plugin source via pip package (not yet fully implemented)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["pip"]
    package: str
    version: str | None = None
    registry: str | None = None


class HTTPSource(BaseModel):
    """Fetch a marketplace manifest via HTTP GET to a URL."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["http"]
    url: str


# Union of typed plugin source objects (used in PluginEntry.source)
PluginSource = Annotated[
    GitHubSource | URLSource | NPMSource | PIPSource | HTTPSource,
    Field(discriminator="source"),
]

# Relative path string (e.g. "./plugins/my-plugin") as plugin source
RelativePathSource = str


class MarketplaceOwner(BaseModel):
    """Owner of a marketplace (from marketplace.json)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    email: str | None = None


class MarketplaceMetadata(BaseModel):
    """Optional metadata for a marketplace."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    description: str | None = None
    version: str | None = None
    plugin_root: str | None = Field(None, alias="pluginRoot")


class PluginEntry(BaseModel):
    """A single plugin entry in a marketplace manifest (name, source, description, etc.)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    source: str | PluginSource  # str = relative path, object = typed source
    description: str | None = None
    version: str | None = None
    author: Author | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    keywords: list[str] = []
    category: str | None = None
    tags: list[str] = []
    strict: bool = True
    # Optional component paths (same semantics as PluginManifest)
    commands: str | list[str] | None = None
    agents: str | list[str] | None = None
    skills: str | list[str] | None = None
    hooks: str | list[str] | dict[str, Any] | None = None
    mcp_servers: str | list[str] | dict[str, Any] | None = Field(None, alias="mcpServers")
    lsp_servers: str | list[str] | dict[str, Any] | None = Field(None, alias="lspServers")


class MarketplaceManifest(BaseModel):
    """Root object of .claude-plugin/marketplace.json (name, owner, plugins list)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    schema_url: str | None = Field(None, alias="$schema")
    name: str
    version: str | None = None
    description: str | None = None
    owner: MarketplaceOwner
    metadata: MarketplaceMetadata | None = None
    plugins: list[PluginEntry]
