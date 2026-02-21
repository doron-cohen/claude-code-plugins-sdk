import json
from pathlib import Path

from claude_code_plugins_sdk.models.agent import AgentDefinition
from claude_code_plugins_sdk.models.command import CommandDefinition
from claude_code_plugins_sdk.models.hook import HooksConfig
from claude_code_plugins_sdk.models.lsp import LSPServerConfig
from claude_code_plugins_sdk.models.mcp import MCPServersConfig
from claude_code_plugins_sdk.models.skill import SkillDefinition

# --- AgentDefinition ---

def test_agent_tools_comma_string():
    """Tools field in YAML is a comma-separated string, not a list."""
    a = AgentDefinition.model_validate({
        "name": "test",
        "description": "A test agent",
        "tools": "Read, Write, Bash",
    })
    assert a.tools == ["Read", "Write", "Bash"]


def test_agent_tools_list_passthrough():
    """Tools can also be a list (future-proofing)."""
    a = AgentDefinition.model_validate({
        "name": "test",
        "description": "A test agent",
        "tools": ["Read", "Write"],
    })
    assert a.tools == ["Read", "Write"]


def test_agent_tools_empty():
    a = AgentDefinition.model_validate({"name": "t", "description": "d", "tools": ""})
    assert a.tools == []


def test_agent_tools_default_empty():
    a = AgentDefinition.model_validate({"name": "t", "description": "d"})
    assert a.tools == []


def test_agent_mcp_wildcard_tool():
    """MCP wildcard tool pattern: mcp__server__*"""
    a = AgentDefinition.model_validate({
        "name": "t",
        "description": "d",
        "tools": "Read, mcp__context7__*, Bash",
    })
    assert "mcp__context7__*" in a.tools


def test_agent_color_optional():
    a = AgentDefinition.model_validate({"name": "t", "description": "d"})
    assert a.color is None


# --- CommandDefinition ---

def test_command_allowed_tools_is_list():
    """allowed-tools in commands is a YAML list, not a comma string."""
    c = CommandDefinition.model_validate({
        "name": "ns:cmd",
        "description": "A command",
        "allowed-tools": ["Read", "Bash", "Task"],
    })
    assert c.allowed_tools == ["Read", "Bash", "Task"]


def test_command_alias():
    """argument-hint maps to argument_hint."""
    c = CommandDefinition.model_validate({
        "argument-hint": "[--strict]",
    })
    assert c.argument_hint == "[--strict]"


def test_command_defaults():
    c = CommandDefinition.model_validate({})
    assert c.allowed_tools == []
    assert c.name is None


# --- SkillDefinition ---

def test_skill_disable_model_invocation_alias():
    s = SkillDefinition.model_validate({"disable-model-invocation": True, "description": "test"})
    assert s.disable_model_invocation is True


def test_skill_defaults():
    s = SkillDefinition.model_validate({})
    assert s.disable_model_invocation is False
    assert s.body == ""


# --- HooksConfig ---

def test_hooks_config():
    data = json.loads(Path("tests/fixtures/plugin/hooks/hooks.json").read_text())
    cfg = HooksConfig.model_validate(data)
    assert "PostToolUse" in cfg.hooks
    assert "SessionStart" in cfg.hooks
    post_use = cfg.hooks["PostToolUse"]
    assert len(post_use) == 1
    assert post_use[0].matcher == "Write|Edit"
    assert post_use[0].hooks[0].type == "command"


# --- MCPServersConfig ---

def test_mcp_config():
    data = json.loads(Path("tests/fixtures/plugin/.mcp.json").read_text())
    cfg = MCPServersConfig.model_validate(data)
    assert "example-db" in cfg.mcp_servers
    assert cfg.mcp_servers["example-db"].command.endswith("db-server")


# --- LSPServerConfig ---

def test_lsp_config():
    data = json.loads(Path("tests/fixtures/plugin/.lsp.json").read_text())
    python_cfg = LSPServerConfig.model_validate(data["python"])
    assert python_cfg.command == "pyright"
    assert python_cfg.extension_to_language[".py"] == "python"
    assert python_cfg.restart_on_crash is True

