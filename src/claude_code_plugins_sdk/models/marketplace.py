from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .plugin import Author  # noqa: TC001


class GitHubSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["github"]
    repo: str  # "owner/repo" format
    ref: str | None = None  # branch or tag
    sha: str | None = None  # full 40-char commit SHA


class URLSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["url"]
    url: str  # must end with .git
    ref: str | None = None
    sha: str | None = None


class NPMSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["npm"]
    package: str
    version: str | None = None
    registry: str | None = None


class PIPSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["pip"]
    package: str
    version: str | None = None
    registry: str | None = None


class HTTPSource(BaseModel):
    """Direct HTTP(S) URL to a marketplace.json file."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["http"]
    url: str


# Discriminated union for typed source objects
PluginSource = Annotated[
    GitHubSource | URLSource | NPMSource | PIPSource | HTTPSource,
    Field(discriminator="source"),
]

# A relative path string (e.g. "./plugins/my-plugin") is also a valid source
RelativePathSource = str


class MarketplaceOwner(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    email: str | None = None


class MarketplaceMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    description: str | None = None
    version: str | None = None
    plugin_root: str | None = Field(None, alias="pluginRoot")


class PluginEntry(BaseModel):
    """A plugin listed in a marketplace manifest."""

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
    """Root object of .claude-plugin/marketplace.json."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    schema_url: str | None = Field(None, alias="$schema")
    name: str
    version: str | None = None
    description: str | None = None
    owner: MarketplaceOwner
    metadata: MarketplaceMetadata | None = None
    plugins: list[PluginEntry]
