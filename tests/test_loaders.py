from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_code_plugins_sdk import (
    LoadError,
    load_agent,
    load_command,
    load_marketplace,
    load_plugin,
    load_skill,
)
from claude_code_plugins_sdk.models.marketplace import GitHubSource

FIXTURE_ROOT = Path("tests/fixtures")


# --- load_marketplace ---

def test_load_marketplace_from_directory():
    m = load_marketplace(FIXTURE_ROOT / "marketplace")
    assert m.name == "example-marketplace"
    assert len(m.plugins) == 5


def test_load_marketplace_from_file():
    m = load_marketplace(FIXTURE_ROOT / "marketplace" / ".claude-plugin" / "marketplace.json")
    assert m.name == "example-marketplace"


def test_load_marketplace_minimal():
    m = load_marketplace(FIXTURE_ROOT / "marketplace" / ".claude-plugin" / "minimal-marketplace.json")
    assert m.name == "minimal-marketplace"


def test_load_marketplace_source_types():
    m = load_marketplace(FIXTURE_ROOT / "marketplace")
    sources = {p.name: p.source for p in m.plugins}
    assert isinstance(sources["local-plugin"], str)
    assert isinstance(sources["github-plugin"], GitHubSource)


def test_load_marketplace_not_found():
    with pytest.raises(LoadError):
        load_marketplace(Path("tests/fixtures/nonexistent"))


def test_load_marketplace_invalid_json(tmp_path):
    bad = tmp_path / ".claude-plugin" / "marketplace.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{ not valid json }")
    with pytest.raises(LoadError):
        load_marketplace(tmp_path)


def test_load_marketplace_invalid_schema(tmp_path):
    bad = tmp_path / ".claude-plugin" / "marketplace.json"
    bad.parent.mkdir(parents=True)
    bad.write_text('{"plugins": []}')  # missing required 'name' and 'owner'
    with pytest.raises(ValidationError):
        load_marketplace(tmp_path)


# --- load_plugin ---

def test_load_plugin_end_to_end():
    p = load_plugin(FIXTURE_ROOT / "plugin")
    assert p.manifest is not None
    assert p.manifest.name == "example-plugin"
    assert len(p.agents) == 2
    assert len(p.commands) == 1
    assert len(p.skills) == 1
    assert p.hooks is not None
    assert p.mcp_servers is not None
    assert p.lsp_servers is not None


def test_load_plugin_agents_tools_parsed():
    p = load_plugin(FIXTURE_ROOT / "plugin")
    reviewer = next(a for a in p.agents if a.name == "example-reviewer")
    assert "Read" in reviewer.tools
    assert "Grep" in reviewer.tools


def test_load_plugin_command_allowed_tools():
    p = load_plugin(FIXTURE_ROOT / "plugin")
    assert p.commands[0].allowed_tools == ["Read", "Grep", "Glob", "Bash"]


def test_load_plugin_skill_body():
    p = load_plugin(FIXTURE_ROOT / "plugin")
    assert len(p.skills[0].body) > 0


def test_load_plugin_not_a_directory():
    with pytest.raises(LoadError):
        load_plugin(FIXTURE_ROOT / "plugin" / ".claude-plugin" / "plugin.json")


def test_load_plugin_no_manifest(tmp_path):
    """A plugin without plugin.json is valid."""
    (tmp_path / "agents").mkdir()
    p = load_plugin(tmp_path)
    assert p.manifest is None
    assert p.agents == []


# --- individual loaders ---

def test_load_agent():
    a = load_agent(FIXTURE_ROOT / "plugin" / "agents" / "reviewer.md")
    assert a.name == "example-reviewer"
    assert a.color == "cyan"
    assert len(a.body) > 0


def test_load_skill():
    s = load_skill(FIXTURE_ROOT / "plugin" / "skills" / "code-review" / "SKILL.md")
    assert s.disable_model_invocation is True
    assert "security" in s.body.lower()


def test_load_command():
    c = load_command(FIXTURE_ROOT / "plugin" / "commands" / "review.md")
    assert c.argument_hint == "[--strict]"
    assert c.agent == "example-reviewer"
