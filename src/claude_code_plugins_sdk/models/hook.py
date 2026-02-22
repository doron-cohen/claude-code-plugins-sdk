from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HookEntry(BaseModel):
    """Single hook action (type and target: command, prompt, or agent)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    type: Literal["command", "prompt", "agent"]
    command: str | None = None
    prompt: str | None = None
    agent: str | None = None


class HookMatcher(BaseModel):
    """Matcher (e.g. event name) and list of hook entries to run."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    matcher: str | None = None
    hooks: list[HookEntry]


# Known hook event names (e.g. PreToolUse, PostToolUse, SessionStart).
HookEvent = Literal[
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "SessionStart",
    "SessionEnd",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "Notification",
    "UserPromptSubmit",
    "PermissionRequest",
    "PreCompact",
    "TaskCompleted",
    "TeammateIdle",
]


class HooksConfig(BaseModel):
    """Contents of hooks/hooks.json: event name -> list of matchers with hook entries."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    hooks: dict[str, list[HookMatcher]] = {}
