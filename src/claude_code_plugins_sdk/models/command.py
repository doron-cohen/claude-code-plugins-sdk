from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CommandDefinition(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str | None = None
    description: str | None = None
    argument_hint: str | None = Field(None, alias="argument-hint")
    allowed_tools: list[str] = Field(default_factory=list, alias="allowed-tools")
    agent: str | None = None
    body: str = ""
