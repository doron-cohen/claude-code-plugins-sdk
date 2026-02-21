from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    command: str
    args: list[str] = []
    env: dict[str, str] = {}
    cwd: str | None = None


class MCPServersConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict, alias="mcpServers")
