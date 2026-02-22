from __future__ import annotations

from typing import Any

from ._result import ValidationIssue, ValidationResult

RESERVED_MARKETPLACE_NAMES = frozenset(
    {
        "claude-code-marketplace",
        "claude-code-plugins",
        "claude-plugins-official",
        "anthropic-marketplace",
        "anthropic-plugins",
        "agent-skills",
        "life-sciences",
    }
)


def validate_marketplace(data: dict[str, Any]) -> ValidationResult:
    issues: list[ValidationIssue] = []

    if "name" not in data or data["name"] is None:
        issues.append(ValidationIssue("error", "name", "name: Required"))
    elif (
        isinstance(data.get("name"), str)
        and data["name"].strip().lower() in RESERVED_MARKETPLACE_NAMES
    ):
        issues.append(
            ValidationIssue("error", "name", f'Marketplace name "{data["name"]}" is reserved')
        )

    if "owner" not in data or data["owner"] is None:
        issues.append(ValidationIssue("error", "owner", "owner: Required"))

    plugins = data.get("plugins")
    if plugins is None:
        issues.append(ValidationIssue("error", "plugins", "plugins: Required"))
    else:
        if isinstance(plugins, list) and len(plugins) == 0:
            issues.append(
                ValidationIssue("warning", "plugins", "Marketplace has no plugins defined")
            )
        elif isinstance(plugins, list):
            seen_names: set[str] = set()
            for i, entry in enumerate(plugins):
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if isinstance(name, str):
                    if name in seen_names:
                        issues.append(
                            ValidationIssue(
                                "error",
                                f"plugins[{i}].name",
                                f'Duplicate plugin name "{name}" found in marketplace',
                            )
                        )
                    seen_names.add(name)

                src = entry.get("source")
                path_prefix = f"plugins[{i}].source"
                if isinstance(src, str):
                    if ".." in src:
                        issues.append(
                            ValidationIssue(
                                "error",
                                path_prefix,
                                "plugins[N].source: Path traversal not allowed",
                            )
                        )
                elif isinstance(src, dict):
                    src_type = src.get("source")
                    plugin_name = entry.get("name") or f"plugins[{i}]"
                    if src_type == "npm":
                        issues.append(
                            ValidationIssue(
                                "warning",
                                path_prefix,
                                f'Plugin "{plugin_name}" uses npm source which is not yet fully implemented',
                            )
                        )
                    elif src_type == "pip":
                        issues.append(
                            ValidationIssue(
                                "warning",
                                path_prefix,
                                f'Plugin "{plugin_name}" uses pip source which is not yet fully implemented',
                            )
                        )

    metadata = data.get("metadata")
    if not metadata or not isinstance(metadata, dict):
        issues.append(
            ValidationIssue(
                "warning",
                "metadata.description",
                "No marketplace description provided.",
            )
        )
    else:
        desc = metadata.get("description")
        if desc is None or (isinstance(desc, str) and not desc.strip()):
            issues.append(
                ValidationIssue(
                    "warning",
                    "metadata.description",
                    "No marketplace description provided.",
                )
            )

    return ValidationResult(issues=issues)
