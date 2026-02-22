# claude-code-plugins-sdk

A Python library for working with Claude Code plugins and marketplaces.

Claude Code has a plugin ecosystem — agents, skills, commands, hooks, MCP servers — but no official Python tooling to work with it. This library lets you load, parse, and validate plugins and marketplaces from disk or from remote sources.

## Install

```bash
pip install claude-code-plugins-sdk
```

Requires Python 3.10+.

## What you can do

Load a local marketplace and inspect its plugins:

```python
from pathlib import Path
from claude_code_plugins_sdk import load_marketplace

marketplace = load_marketplace(Path("./my-marketplace"))

for plugin in marketplace.plugins:
    print(plugin.name, plugin.version)
```

Fetch a marketplace from GitHub:

```python
from claude_code_plugins_sdk import fetch_marketplace

# GitHub shorthand
marketplace = fetch_marketplace("anthropics/claude-code")

# Pinned to a tag
from claude_code_plugins_sdk import GitHubSource
marketplace = fetch_marketplace(GitHubSource(source="github", repo="anthropics/claude-code", ref="v1.0"))

# Raw URL to a marketplace.json
marketplace = fetch_marketplace("https://example.com/.claude-plugin/marketplace.json")
```

Load a plugin directory and read its agents, skills, commands, and hooks:

```python
from pathlib import Path
from claude_code_plugins_sdk import load_plugin

plugin = load_plugin(Path("./my-plugin"))

print(plugin.manifest.name)       # plugin name from plugin.json
print(plugin.agents)              # list of AgentDefinition
print(plugin.skills)              # list of SkillDefinition
print(plugin.commands)            # list of CommandDefinition
print(plugin.hooks)               # HooksConfig or None
print(plugin.mcp_servers)         # MCPServersConfig or None
```

Load individual component files directly:

```python
from claude_code_plugins_sdk import load_agent, load_skill, load_command

agent = load_agent(Path("./agents/reviewer.md"))
print(agent.name, agent.tools)   # tools is always a list, even though YAML stores it as a comma string

skill = load_skill(Path("./skills/code-review/SKILL.md"))
command = load_command(Path("./commands/review.md"))
```

## Plugin structure

A Claude Code plugin is a directory with this layout:

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json      # optional manifest
├── agents/              # *.md files with YAML frontmatter
├── skills/              # */SKILL.md files
├── commands/            # *.md files
├── hooks/
│   └── hooks.json
├── .mcp.json
└── .lsp.json
```

A marketplace is a directory with `.claude-plugin/marketplace.json` listing plugins and where to find them.

## Development

```bash
git clone git@github.com:doron-cohen/claude-code-plugins-sdk.git
cd claude-code-plugins-sdk
uv sync
uv run pytest
```

```bash
uv run pytest -m integration  # hits real remote marketplaces, needs network
```
