from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ValidationIssue:
    """A single validation finding (error or warning)."""

    level: Literal["error", "warning"]
    path: str  # JSON path or field name where the issue was found
    message: str


@dataclass
class ValidationResult:
    """Result of validating a plugin or marketplace manifest.

    Attributes:
        issues: All errors and warnings. Use .errors and .warnings for filtered views.
        valid: True if there are no errors (warnings are allowed).
    """

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
