from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HookEntry(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    type: Literal["command", "prompt", "agent"]
    command: str | None = None
    prompt: str | None = None
    agent: str | None = None


class HookMatcher(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    matcher: str | None = None
    hooks: list[HookEntry]


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
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    hooks: dict[str, list[HookMatcher]] = {}
