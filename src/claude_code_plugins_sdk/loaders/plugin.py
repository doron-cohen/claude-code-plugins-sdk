from __future__ import annotations

import json
from typing import TYPE_CHECKING, TypeVar

import frontmatter  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from pathlib import Path

from pydantic import BaseModel

from .._plugin import Plugin
from ..errors import LoadError
from ..models.agent import AgentDefinition
from ..models.command import CommandDefinition
from ..models.hook import HooksConfig
from ..models.lsp import LSPServerConfig, LSPServersConfig
from ..models.mcp import MCPServersConfig
from ..models.plugin import PluginManifest
from ..models.skill import SkillDefinition

_T = TypeVar("_T", bound=BaseModel)


def load_plugin(path: Path) -> Plugin:
    """Load a plugin from its root directory.

    Discovers all components at their default locations. The plugin manifest
    at .claude-plugin/plugin.json is optional.
    """
    if not path.is_dir():
        raise LoadError(f"Plugin path is not a directory: {path}", path=path)

    manifest = _load_optional_manifest(path)
    agents = _discover_agents(path)
    commands = _discover_commands(path)
    skills = _discover_skills(path)
    hooks = _load_optional_json(path / "hooks" / "hooks.json", HooksConfig)
    mcp_servers = _load_optional_json(path / ".mcp.json", MCPServersConfig)
    lsp_servers = _load_optional_lsp(path / ".lsp.json")

    return Plugin(
        root=path,
        manifest=manifest,
        agents=agents,
        commands=commands,
        skills=skills,
        hooks=hooks,
        mcp_servers=mcp_servers,
        lsp_servers=lsp_servers,
    )


def load_agent(path: Path) -> AgentDefinition:
    """Load a single agent definition from a .md file."""
    post = _load_frontmatter(path)
    data = dict(post.metadata)
    data["body"] = post.content
    return AgentDefinition.model_validate(data)


def load_skill(path: Path) -> SkillDefinition:
    """Load a skill definition from a SKILL.md file."""
    post = _load_frontmatter(path)
    data = dict(post.metadata)
    data["body"] = post.content
    return SkillDefinition.model_validate(data)


def load_command(path: Path) -> CommandDefinition:
    """Load a command definition from a .md file."""
    post = _load_frontmatter(path)
    data = dict(post.metadata)
    data["body"] = post.content
    return CommandDefinition.model_validate(data)


# --- internal helpers ---


def _load_frontmatter(path: Path) -> frontmatter.Post:
    try:
        return frontmatter.load(str(path))
    except FileNotFoundError as e:
        raise LoadError(f"File not found: {path}", path=path) from e
    except Exception as e:
        raise LoadError(f"Failed to parse {path}: {e}", path=path) from e


def _load_optional_manifest(root: Path) -> PluginManifest | None:
    manifest_path = root / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LoadError(f"Invalid JSON in {manifest_path}: {e}", path=manifest_path) from e
    return PluginManifest.model_validate(data)


def _discover_agents(root: Path) -> list[AgentDefinition]:
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return []
    return [load_agent(f) for f in sorted(agents_dir.glob("*.md"))]


def _discover_commands(root: Path) -> list[CommandDefinition]:
    commands_dir = root / "commands"
    if not commands_dir.is_dir():
        return []
    return [load_command(f) for f in sorted(commands_dir.glob("*.md"))]


def _discover_skills(root: Path) -> list[SkillDefinition]:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return []
    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skills.append(load_skill(skill_md))
    return skills


def _load_optional_json(path: Path, model_class: type[_T]) -> _T | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LoadError(f"Invalid JSON in {path}: {e}", path=path) from e
    return model_class.model_validate(data)


def _load_optional_lsp(path: Path) -> LSPServersConfig | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise LoadError(f"Invalid JSON in {path}: {e}", path=path) from e
    return {name: LSPServerConfig.model_validate(cfg) for name, cfg in data.items()}
