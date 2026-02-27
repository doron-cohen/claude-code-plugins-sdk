"""Tests for AgentRuntime — list, get, and search skills."""

from pathlib import Path

import pytest

from claude_code_plugins_sdk.agent import AgentRuntime, SkillMatch, SkillSummary

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
