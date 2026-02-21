from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SkillDefinition(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str | None = None
    description: str | None = None
    disable_model_invocation: bool = Field(False, alias="disable-model-invocation")
    body: str = ""
