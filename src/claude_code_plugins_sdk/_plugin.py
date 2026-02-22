from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .models.agent import AgentDefinition
    from .models.command import CommandDefinition
    from .models.hook import HooksConfig
    from .models.lsp import LSPServersConfig
    from .models.mcp import MCPServersConfig
    from .models.plugin import PluginManifest
    from .models.skill import SkillDefinition


@dataclass
class Plugin:
    """A loaded Claude Code plugin directory.

    Attributes:
        root: Path to the plugin directory.
        manifest: Parsed .claude-plugin/plugin.json, or None if absent.
        agents: Discovered agent definitions from agents/*.md.
        commands: Discovered command definitions from commands/*.md.
        skills: Discovered skill definitions from skills/*/SKILL.md.
        hooks: Parsed hooks/hooks.json, or None if absent.
        mcp_servers: Parsed .mcp.json, or None if absent.
        lsp_servers: Parsed .lsp.json (name -> config), or None if absent.
    """

    root: Path
    manifest: PluginManifest | None = None
    agents: list[AgentDefinition] = field(default_factory=list)
    commands: list[CommandDefinition] = field(default_factory=list)
    skills: list[SkillDefinition] = field(default_factory=list)
    hooks: HooksConfig | None = None
    mcp_servers: MCPServersConfig | None = None
    lsp_servers: LSPServersConfig | None = None
