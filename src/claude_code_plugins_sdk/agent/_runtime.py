"""AgentRuntime — discover and load skills from installed, enabled plugins."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..manager._manager import PluginManager


@dataclass(frozen=True)
class SkillSummary:
    """Lightweight skill metadata — no body loaded."""

    plugin: str
    slug: str  # directory name under skills/
    name: str | None
    description: str | None
    disable_model_invocation: bool = False

    @property
    def id(self) -> str:
        return f"{self.plugin}:{self.slug}"


@dataclass(frozen=True)
class SkillMatch:
    """A skill with a relevance score from a search."""

    skill: SkillSummary
    score: float  # 0.0–1.0


@dataclass(frozen=True)
class CommandSummary:
    """Lightweight command metadata — no body loaded."""

    plugin: str
    slug: str  # file stem, e.g. "review"
    name: str | None
    description: str | None
    argument_hint: str | None = None
    allowed_tools: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.plugin}:{self.slug}"


@dataclass(frozen=True)
class CommandMatch:
    """A command with a relevance score from a search."""

    command: CommandSummary
    score: float  # 0.0–1.0


@dataclass(frozen=True)
class AgentSummary:
    """Lightweight agent metadata — no body loaded."""

    plugin: str
    slug: str  # file stem, e.g. "reviewer"
    name: str | None
    description: str | None
    tools: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.plugin}:{self.slug}"


@dataclass(frozen=True)
class AgentMatch:
    """An agent with a relevance score from a search."""

    agent: AgentSummary
    score: float  # 0.0–1.0


@dataclass
class AgentRuntime:
    """Read-only view of skills from installed, enabled plugins.

    Build from a PluginManager:

        runtime = AgentRuntime.from_manager(manager)
        skills = runtime.list_skills()
        results = runtime.search_skills("code review")
        full = runtime.get_skill("my-plugin", "code-review")
    """

    _index: list[tuple[SkillSummary, Path]] = field(default_factory=list, repr=False)
    _cmd_index: list[tuple[CommandSummary, Path]] = field(default_factory=list, repr=False)
    _agent_index: list[tuple[AgentSummary, Path]] = field(default_factory=list, repr=False)

    # --- factory ---

    @classmethod
    def from_manager(cls, manager: PluginManager) -> AgentRuntime:
        """Build a runtime by loading skills from all installed, enabled plugins."""
        runtime = cls()
        seen_plugins: set[str] = set()

        for installed in manager.list_installed():
            if not installed.enabled:
                continue
            if installed.name in seen_plugins:
                continue
            seen_plugins.add(installed.name)

            plugin_dir = _resolve_plugin_dir(manager, installed.name, installed.marketplace)
            if plugin_dir is None:
                continue

            skills_dir = plugin_dir / "skills"
            if skills_dir.is_dir():
                for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                    slug = skill_md.parent.name
                    try:
                        skill_def = _load_skill_meta(skill_md)
                    except Exception:
                        continue
                    summary = SkillSummary(
                        plugin=installed.name,
                        slug=slug,
                        name=skill_def.get("name"),
                        description=skill_def.get("description"),
                        disable_model_invocation=bool(
                            skill_def.get("disable-model-invocation", False)
                        ),
                    )
                    runtime._index.append((summary, skill_md))

            _index_commands_and_agents(runtime, installed.name, plugin_dir)

        return runtime

    @classmethod
    def from_plugins(cls, plugins: list[tuple[str, Path]]) -> AgentRuntime:
        """Build a runtime from explicit (plugin_name, plugin_dir) pairs.

        Useful for testing or when you manage plugin paths yourself.
        """
        runtime = cls()
        for plugin_name, plugin_dir in plugins:
            skills_dir = plugin_dir / "skills"
            if skills_dir.is_dir():
                for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                    slug = skill_md.parent.name
                    try:
                        skill_def = _load_skill_meta(skill_md)
                    except Exception:
                        continue
                    summary = SkillSummary(
                        plugin=plugin_name,
                        slug=slug,
                        name=skill_def.get("name"),
                        description=skill_def.get("description"),
                        disable_model_invocation=bool(
                            skill_def.get("disable-model-invocation", False)
                        ),
                    )
                    runtime._index.append((summary, skill_md))

            _index_commands_and_agents(runtime, plugin_name, plugin_dir)

        return runtime

    # --- public API ---

    def list_skills(self) -> list[SkillSummary]:
        """Return metadata for all available skills. No body loaded."""
        return [summary for summary, _ in self._index]

    def get_skill(self, plugin: str, slug: str) -> str:
        """Return the full SKILL.md body for a skill.

        Args:
            plugin: Plugin name (as in SkillSummary.plugin).
            slug: Skill directory name (as in SkillSummary.slug).

        Returns:
            Full markdown content of the SKILL.md file.

        Raises:
            KeyError: If no matching skill is found.
        """
        for summary, path in self._index:
            if summary.plugin == plugin and summary.slug == slug:
                return path.read_text(encoding="utf-8")
        raise KeyError(f"Skill not found: {plugin}:{slug}")

    def search_skills(self, query: str, limit: int = 10) -> list[SkillMatch]:
        """Search skills by name and description using in-memory token matching.

        Scores each skill by how many query tokens appear in its name+description.
        Returns results sorted by score descending, ties broken by skill id.

        Args:
            query: Free-text search query.
            limit: Maximum number of results to return.

        Returns:
            List of SkillMatch sorted by relevance (highest first).
        """
        tokens = _tokenize(query)
        if not tokens:
            return [SkillMatch(skill=s, score=1.0) for s, _ in self._index[:limit]]

        results: list[SkillMatch] = []
        for summary, _ in self._index:
            score = _score(summary, tokens)
            if score > 0:
                results.append(SkillMatch(skill=summary, score=score))

        results.sort(key=lambda m: (-m.score, m.skill.id))
        return results[:limit]

    def list_commands(self) -> list[CommandSummary]:
        """Return metadata for all available commands. No body loaded."""
        return [s for s, _ in self._cmd_index]

    def get_command(self, plugin: str, slug: str) -> str:
        """Return the full body for a command.

        Args:
            plugin: Plugin name (as in CommandSummary.plugin).
            slug: Command file stem (as in CommandSummary.slug).

        Returns:
            Full markdown content of the command file.

        Raises:
            KeyError: If no matching command is found.
        """
        for s, path in self._cmd_index:
            if s.plugin == plugin and s.slug == slug:
                return path.read_text(encoding="utf-8")
        raise KeyError(f"Command not found: {plugin}:{slug}")

    def search_commands(self, query: str, limit: int = 10) -> list[CommandMatch]:
        """Search commands by name and description using in-memory token matching.

        Args:
            query: Free-text search query.
            limit: Maximum number of results to return.

        Returns:
            List of CommandMatch sorted by relevance (highest first).
        """
        tokens = _tokenize(query)
        if not tokens:
            return [CommandMatch(command=s, score=1.0) for s, _ in self._cmd_index[:limit]]
        results = []
        for s, _ in self._cmd_index:
            sc = _score_fields(s.name, s.description, s.slug, s.plugin, tokens)
            if sc > 0:
                results.append(CommandMatch(command=s, score=sc))
        results.sort(key=lambda m: (-m.score, m.command.id))
        return results[:limit]

    def list_agents(self) -> list[AgentSummary]:
        """Return metadata for all available agents. No body loaded."""
        return [s for s, _ in self._agent_index]

    def get_agent(self, plugin: str, slug: str) -> str:
        """Return the full body for an agent.

        Args:
            plugin: Plugin name (as in AgentSummary.plugin).
            slug: Agent file stem (as in AgentSummary.slug).

        Returns:
            Full markdown content of the agent file.

        Raises:
            KeyError: If no matching agent is found.
        """
        for s, path in self._agent_index:
            if s.plugin == plugin and s.slug == slug:
                return path.read_text(encoding="utf-8")
        raise KeyError(f"Agent not found: {plugin}:{slug}")

    def search_agents(self, query: str, limit: int = 10) -> list[AgentMatch]:
        """Search agents by name and description using in-memory token matching.

        Args:
            query: Free-text search query.
            limit: Maximum number of results to return.

        Returns:
            List of AgentMatch sorted by relevance (highest first).
        """
        tokens = _tokenize(query)
        if not tokens:
            return [AgentMatch(agent=s, score=1.0) for s, _ in self._agent_index[:limit]]
        results = []
        for s, _ in self._agent_index:
            sc = _score_fields(s.name, s.description, s.slug, s.plugin, tokens)
            if sc > 0:
                results.append(AgentMatch(agent=s, score=sc))
        results.sort(key=lambda m: (-m.score, m.agent.id))
        return results[:limit]


# --- internal helpers ---


def _index_commands_and_agents(runtime: AgentRuntime, plugin_name: str, plugin_dir: Path) -> None:
    """Index commands and agents from a plugin directory into the runtime."""
    commands_dir = plugin_dir / "commands"
    if commands_dir.is_dir():
        for cmd_md in sorted(commands_dir.glob("*.md")):
            slug = cmd_md.stem
            try:
                meta = _load_skill_meta(cmd_md)
            except Exception:
                continue
            tools = meta.get("allowed-tools") or []
            if isinstance(tools, str):
                tools = [t.strip() for t in tools.split(",") if t.strip()]
            summary = CommandSummary(
                plugin=plugin_name,
                slug=slug,
                name=meta.get("name"),
                description=meta.get("description"),
                argument_hint=meta.get("argument-hint"),
                allowed_tools=tools,
            )
            runtime._cmd_index.append((summary, cmd_md))

    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        for agent_md in sorted(agents_dir.glob("*.md")):
            slug = agent_md.stem
            try:
                meta = _load_skill_meta(agent_md)
            except Exception:
                continue
            tools_raw = meta.get("tools") or []
            if isinstance(tools_raw, str):
                tools_raw = [t.strip() for t in tools_raw.split(",") if t.strip()]
            summary = AgentSummary(
                plugin=plugin_name,
                slug=slug,
                name=meta.get("name"),
                description=meta.get("description"),
                tools=tools_raw,
            )
            runtime._agent_index.append((summary, agent_md))


def _resolve_plugin_dir(manager: PluginManager, plugin_name: str, marketplace: str) -> Path | None:
    """Find the plugin directory within a marketplace cache."""
    # Check plugin-specific cache first (for externally-sourced plugins)
    try:
        plugin_cache = manager._state.get_plugin_cache_path(marketplace, plugin_name)
        if plugin_cache.is_dir():
            return plugin_cache
    except Exception:
        pass

    try:
        cache_path = manager._state.get_cache_path(marketplace)
    except Exception:
        return None

    # Marketplace caches can store plugins under plugins/ or external_plugins/
    for subdir in ("plugins", "external_plugins"):
        candidate = cache_path / subdir / plugin_name
        if candidate.is_dir():
            return candidate

    # Or the plugin might be the root of the cache itself
    if (cache_path / ".claude-plugin").is_dir():
        return cache_path

    return None


def _load_skill_meta(path: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md without loading the body model."""
    import frontmatter

    post = frontmatter.load(str(path))
    return dict(post.metadata)


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _score_fields(
    name: str | None,
    description: str | None,
    slug: str,
    plugin: str,
    query_tokens: list[str],
) -> float:
    """Score fields against query tokens. Returns 0.0–1.0."""
    haystack = " ".join(filter(None, [name, description, slug, plugin]))
    hay_tokens = set(_tokenize(haystack))
    if not hay_tokens:
        return 0.0

    # Name/slug matches are weighted higher than description matches
    name_tokens = set(_tokenize(" ".join(filter(None, [name, slug]))))
    desc_tokens = set(_tokenize(description or ""))

    hits = 0.0
    for t in query_tokens:
        if t in name_tokens:
            hits += 2.0
        elif t in desc_tokens:
            hits += 1.0

    return min(hits / (len(query_tokens) * 2.0), 1.0)


def _score(summary: SkillSummary, query_tokens: list[str]) -> float:
    """Thin wrapper kept for backward compatibility."""
    return _score_fields(
        summary.name, summary.description, summary.slug, summary.plugin, query_tokens
    )
