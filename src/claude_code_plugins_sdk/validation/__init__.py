from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from ._marketplace import validate_marketplace as _validate_marketplace
from ._plugin import validate_plugin as _validate_plugin
from ._result import ValidationIssue, ValidationResult


def validate_marketplace(data: dict[str, Any]) -> ValidationResult:
    """Validate a marketplace manifest dict (e.g. from marketplace.json).

    Checks required fields, reserved names, duplicate plugin names, and path safety.
    """
    return _validate_marketplace(data)


def validate_plugin(data: dict[str, Any]) -> ValidationResult:
    """Validate a plugin manifest dict (e.g. from plugin.json)."""
    return _validate_plugin(data)


def validate_marketplace_file(path: Path) -> ValidationResult:
    """Load and validate a marketplace.json file from disk."""
    data = json.loads(path.read_text())
    return _validate_marketplace(data)


def validate_plugin_file(path: Path) -> ValidationResult:
    """Load and validate a plugin.json file from disk."""
    data = json.loads(path.read_text())
    return _validate_plugin(data)


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_marketplace",
    "validate_marketplace_file",
    "validate_plugin",
    "validate_plugin_file",
]
