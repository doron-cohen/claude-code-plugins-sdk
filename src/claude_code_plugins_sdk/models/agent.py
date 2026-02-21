from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    description: str
    tools: list[str] = []
    color: str | None = None
    body: str = ""

    @field_validator("tools", mode="before")
    @classmethod
    def _parse_tools_string(cls, v: object) -> object:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
