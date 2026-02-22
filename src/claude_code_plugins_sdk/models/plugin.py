from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Author(BaseModel):
    """Plugin or marketplace author."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    email: str | None = None
    url: str | None = None


class PluginManifest(BaseModel):
    """Contents of .claude-plugin/plugin.json."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    version: str | None = None
    description: str | None = None
    author: Author | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    keywords: list[str] = []
    # Component path fields — each accepts a path string, list of paths, or inline config dict
    commands: str | list[str] | None = None
    agents: str | list[str] | None = None
    skills: str | list[str] | None = None
    hooks: str | list[str] | dict[str, Any] | None = None
    mcp_servers: str | list[str] | dict[str, Any] | None = Field(None, alias="mcpServers")
    output_styles: str | list[str] | None = Field(None, alias="outputStyles")
    lsp_servers: str | list[str] | dict[str, Any] | None = Field(None, alias="lspServers")
