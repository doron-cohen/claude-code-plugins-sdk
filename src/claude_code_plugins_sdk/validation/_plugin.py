from __future__ import annotations

from typing import Any

from ._result import ValidationIssue, ValidationResult


def validate_plugin(data: dict[str, Any]) -> ValidationResult:
    issues: list[ValidationIssue] = []

    name = data.get("name")
    if name is None or (isinstance(name, str) and not name.strip()):
        issues.append(ValidationIssue("error", "name", "name: Required"))

    return ValidationResult(issues=issues)
