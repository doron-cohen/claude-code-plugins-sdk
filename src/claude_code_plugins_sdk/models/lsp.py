from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class LSPServerConfig(BaseModel):
    """Configuration for a single LSP server (command, args, transport, options)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    command: str
    extension_to_language: dict[str, str] = Field(default_factory=dict, alias="extensionToLanguage")
    args: list[str] = []
    transport: Literal["stdio", "socket"] = "stdio"
    env: dict[str, str] = {}
    initialization_options: dict[str, Any] | None = Field(None, alias="initializationOptions")
    settings: dict[str, Any] | None = None
    workspace_folder: str | None = Field(None, alias="workspaceFolder")
    startup_timeout: int | None = Field(None, alias="startupTimeout")
    shutdown_timeout: int | None = Field(None, alias="shutdownTimeout")
    restart_on_crash: bool | None = Field(None, alias="restartOnCrash")
    max_restarts: int | None = Field(None, alias="maxRestarts")


# Name -> LSPServerConfig (e.g. from .lsp.json)
LSPServersConfig = dict[str, LSPServerConfig]
