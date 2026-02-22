from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ValidationIssue:
    level: Literal["error", "warning"]
    path: str
    message: str


@dataclass
class ValidationResult:
    issues: list[ValidationIssue]

    @property
    def valid(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]
