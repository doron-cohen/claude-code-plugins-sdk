import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_code_plugins_sdk.models.plugin import Author, PluginManifest


def test_plugin_manifest_full():
    data = json.loads(
        (Path("tests/fixtures/plugin/.claude-plugin/plugin.json")).read_text()
    )
    m = PluginManifest.model_validate(data)
    assert m.name == "example-plugin"
    assert m.version == "1.2.0"
    assert m.author is not None
    assert m.author.name == "Test Author"
    assert m.license == "MIT"


def test_plugin_manifest_minimal():
    m = PluginManifest.model_validate({"name": "my-plugin"})
    assert m.name == "my-plugin"
    assert m.version is None
    assert m.keywords == []


def test_plugin_manifest_missing_name():
    with pytest.raises(ValidationError):
        PluginManifest.model_validate({})


def test_author_optional_fields():
    a = Author.model_validate({"name": "Alice"})
    assert a.email is None
    assert a.url is None


def test_plugin_component_paths():
    m = PluginManifest.model_validate({
        "name": "p",
        "commands": "./custom/cmd.md",
        "agents": ["./a1.md", "./a2.md"],
        "mcpServers": "./mcp.json",
    })
    assert m.commands == "./custom/cmd.md"
    assert isinstance(m.agents, list)
    assert m.mcp_servers == "./mcp.json"
