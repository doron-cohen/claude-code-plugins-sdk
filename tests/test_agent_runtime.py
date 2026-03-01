"""Tests for AgentRuntime — list, get, and search skills."""

from pathlib import Path

import pytest

from claude_code_plugins_sdk.agent import (
    AgentMatch,
    AgentRuntime,
    AgentSummary,
    CommandMatch,
    CommandSummary,
    SkillMatch,
    SkillSummary,
)

PLUGIN_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "plugin"


def _runtime() -> AgentRuntime:
    return AgentRuntime.from_plugins([("test-plugin", PLUGIN_FIXTURE)])


# --- list_skills ---


def test_list_skills_returns_summaries():
    skills = _runtime().list_skills()
    assert len(skills) == 1
    skill = skills[0]
    assert isinstance(skill, SkillSummary)
    assert skill.plugin == "test-plugin"
    assert skill.slug == "code-review"


def test_list_skills_no_body():
    skill = _runtime().list_skills()[0]
    # SkillSummary has no body attribute
    assert not hasattr(skill, "body")


def test_list_skills_metadata():
    skill = _runtime().list_skills()[0]
    assert skill.description == "Review code for bugs, security issues, and quality improvements"
    assert skill.disable_model_invocation is True


def test_skill_id():
    skill = _runtime().list_skills()[0]
    assert skill.id == "test-plugin:code-review"


def test_list_skills_empty_for_no_skills(tmp_path: Path):
    runtime = AgentRuntime.from_plugins([("empty-plugin", tmp_path)])
    assert runtime.list_skills() == []


# --- get_skill ---


def test_get_skill_returns_full_content():
    body = _runtime().get_skill("test-plugin", "code-review")
    assert "Review the provided code" in body
    assert "security" in body.lower()


def test_get_skill_includes_frontmatter():
    body = _runtime().get_skill("test-plugin", "code-review")
    # Full SKILL.md file — frontmatter is included
    assert "---" in body


def test_get_skill_unknown_raises():
    with pytest.raises(KeyError, match="test-plugin:no-such"):
        _runtime().get_skill("test-plugin", "no-such")


def test_get_skill_unknown_plugin_raises():
    with pytest.raises(KeyError, match="other-plugin:code-review"):
        _runtime().get_skill("other-plugin", "code-review")


# --- search_skills ---


def test_search_skills_match_by_description():
    results = _runtime().search_skills("security")
    assert len(results) == 1
    assert isinstance(results[0], SkillMatch)
    assert results[0].skill.slug == "code-review"
    assert results[0].score > 0


def test_search_skills_no_match_returns_empty():
    results = _runtime().search_skills("unrelated xyz123")
    assert results == []


def test_search_skills_empty_query_returns_all():
    results = _runtime().search_skills("")
    assert len(results) == 1


def test_search_skills_limit(tmp_path: Path):
    # Build a runtime with multiple skills
    skills_dir = tmp_path / "skills"
    for i in range(5):
        d = skills_dir / f"skill-{i}"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: skill-{i}\ndescription: test skill number {i}\n---\nBody {i}.\n",
            encoding="utf-8",
        )
    runtime = AgentRuntime.from_plugins([("multi-plugin", tmp_path)])
    results = runtime.search_skills("test skill", limit=3)
    assert len(results) <= 3


def test_search_skills_score_name_higher_than_description(tmp_path: Path):
    skills_dir = tmp_path / "skills"

    # skill-a: "review" only in description
    a = skills_dir / "skill-a"
    a.mkdir(parents=True)
    (a / "SKILL.md").write_text(
        "---\nname: helper\ndescription: does a review of things\n---\nBody.\n",
        encoding="utf-8",
    )

    # skill-b: "review" in name
    b = skills_dir / "skill-b"
    b.mkdir(parents=True)
    (b / "SKILL.md").write_text(
        "---\nname: review\ndescription: helps with stuff\n---\nBody.\n",
        encoding="utf-8",
    )

    runtime = AgentRuntime.from_plugins([("p", tmp_path)])
    results = runtime.search_skills("review")
    assert len(results) == 2
    # skill-b (name match) should rank above skill-a (description match)
    assert results[0].skill.slug == "skill-b"
    assert results[0].score > results[1].score


# --- from_manager integration ---


def test_from_manager_only_enabled_plugins():
    """from_manager skips disabled plugins."""
    from contextlib import contextmanager

    from claude_code_plugins_sdk import PluginManager
    from claude_code_plugins_sdk.manager._in_memory import (
        InMemoryMarketplaceAdapter,
        InMemorySettingsAdapter,
    )
    from claude_code_plugins_sdk.models.state import GitHubMarketplaceSource, KnownMarketplaceEntry

    @contextmanager
    def _noop_fetch(source):
        yield PLUGIN_FIXTURE

    class _MockFetch:
        def fetch(self, source):
            return _noop_fetch(source)

    from datetime import datetime, timezone

    entry = KnownMarketplaceEntry(
        source=GitHubMarketplaceSource(source="github", repo="owner/repo"),
        installLocation=PLUGIN_FIXTURE,
        lastUpdated=datetime.now(timezone.utc),
    )
    marketplace_adapter = InMemoryMarketplaceAdapter(marketplaces={"test-marketplace": entry})
    # Plugin installed but disabled
    settings = InMemorySettingsAdapter({"test-plugin@test-marketplace": False})
    manager = PluginManager(
        marketplace_state=marketplace_adapter,
        settings={"user": settings},
        fetcher=_MockFetch(),
    )
    runtime = AgentRuntime.from_manager(manager)
    assert runtime.list_skills() == []


# --- list_commands ---


def test_list_commands_returns_summaries():
    commands = _runtime().list_commands()
    assert len(commands) == 1
    cmd = commands[0]
    assert isinstance(cmd, CommandSummary)
    assert cmd.plugin == "test-plugin"
    assert cmd.slug == "review"
    assert cmd.name == "example-plugin:review"
    assert cmd.description == "Run a code review on the current changes"
    assert cmd.argument_hint == "[--strict]"
    assert cmd.allowed_tools == ["Read", "Grep", "Glob", "Bash"]


# --- list_agents ---


def test_list_agents_returns_summaries():
    agents = _runtime().list_agents()
    assert len(agents) == 2
    slugs = {a.slug for a in agents}
    assert slugs == {"minimal", "reviewer"}
    for agent in agents:
        assert isinstance(agent, AgentSummary)
        assert agent.plugin == "test-plugin"

    reviewer = next(a for a in agents if a.slug == "reviewer")
    assert reviewer.tools == ["Read", "Grep", "Glob", "WebSearch"]

    minimal = next(a for a in agents if a.slug == "minimal")
    assert minimal.tools == ["Read"]


# --- get_command ---


def test_get_command_returns_full_body():
    body = _runtime().get_command("test-plugin", "review")
    assert "---" in body
    assert "Run a comprehensive code review" in body


def test_get_command_missing_raises_key_error():
    with pytest.raises(KeyError, match="test-plugin:no-such"):
        _runtime().get_command("test-plugin", "no-such")


# --- get_agent ---


def test_get_agent_returns_full_body():
    body = _runtime().get_agent("test-plugin", "reviewer")
    assert "---" in body
    assert "code reviewer" in body


def test_get_agent_missing_raises_key_error():
    with pytest.raises(KeyError, match="test-plugin:no-such"):
        _runtime().get_agent("test-plugin", "no-such")


# --- search_commands ---


def test_search_commands_scores_by_name():
    results = _runtime().search_commands("review")
    assert len(results) >= 1
    assert isinstance(results[0], CommandMatch)
    assert results[0].command.slug == "review"
    assert results[0].score > 0


def test_search_commands_empty_query_returns_all():
    results = _runtime().search_commands("")
    assert len(results) == 1


# --- search_agents ---


def test_search_agents_scores_by_name():
    results = _runtime().search_agents("reviewer")
    assert len(results) >= 1
    assert isinstance(results[0], AgentMatch)
    assert results[0].agent.slug == "reviewer"
    assert results[0].score > 0


def test_search_agents_empty_query_returns_all():
    results = _runtime().search_agents("")
    assert len(results) == 2


# --- from_manager loads commands and agents ---


def test_from_manager_loads_commands_and_agents():
    from contextlib import contextmanager
    from datetime import datetime, timezone

    from claude_code_plugins_sdk import PluginManager
    from claude_code_plugins_sdk.manager._in_memory import (
        InMemoryMarketplaceAdapter,
        InMemorySettingsAdapter,
    )
    from claude_code_plugins_sdk.models.state import GitHubMarketplaceSource, KnownMarketplaceEntry

    @contextmanager
    def _noop_fetch(source):
        yield PLUGIN_FIXTURE

    class _MockFetch:
        def fetch(self, source):
            return _noop_fetch(source)

    entry = KnownMarketplaceEntry(
        source=GitHubMarketplaceSource(source="github", repo="owner/repo"),
        installLocation=PLUGIN_FIXTURE,
        lastUpdated=datetime.now(timezone.utc),
    )
    marketplace_adapter = InMemoryMarketplaceAdapter(marketplaces={"test-marketplace": entry})
    # Wire up the plugin cache so _resolve_plugin_dir can find the fixture
    marketplace_adapter._plugin_cache[("test-marketplace", "test-plugin")] = PLUGIN_FIXTURE
    settings = InMemorySettingsAdapter({"test-plugin@test-marketplace": True})
    manager = PluginManager(
        marketplace_state=marketplace_adapter,
        settings={"user": settings},
        fetcher=_MockFetch(),
    )
    runtime = AgentRuntime.from_manager(manager)
    assert len(runtime.list_commands()) >= 1
    assert len(runtime.list_agents()) >= 1
