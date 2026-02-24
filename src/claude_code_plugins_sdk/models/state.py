"""State file models for known_marketplaces.json and blocklist.json."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class GitHubMarketplaceSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["github"]
    repo: str
    ref: str | None = None


class GitMarketplaceSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["git"]
    url: str
    ref: str | None = None


class DirectoryMarketplaceSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["directory"]
    path: str


class HostPatternMarketplaceSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["hostPattern"]
    host_pattern: str = Field(alias="hostPattern")


class HttpMarketplaceSource(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: Literal["http"]
    url: str


AnyMarketplaceSource = Annotated[
    GitHubMarketplaceSource
    | GitMarketplaceSource
    | DirectoryMarketplaceSource
    | HostPatternMarketplaceSource
    | HttpMarketplaceSource,
    Field(discriminator="source"),
]


class KnownMarketplaceEntry(BaseModel):
    """Single entry in known_marketplaces.json."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: AnyMarketplaceSource
    install_location: Path = Field(alias="installLocation")
    last_updated: datetime = Field(alias="lastUpdated")


class BlocklistPlugin(BaseModel):
    """Single blocked plugin in blocklist.json."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    plugin: str  # "name@marketplace"
    added_at: datetime
    reason: str | None = None
    text: str | None = None


class BlocklistFile(BaseModel):
    """Root of blocklist.json."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    fetched_at: datetime = Field(alias="fetchedAt")
    plugins: list[BlocklistPlugin] = []
