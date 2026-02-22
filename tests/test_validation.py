from pathlib import Path

from claude_code_plugins_sdk import (
    ValidationIssue,
    ValidationResult,
    validate_marketplace,
    validate_marketplace_file,
    validate_plugin,
    validate_plugin_file,
)

FIXTURE_ROOT = Path("tests/fixtures")


def test_marketplace_valid_no_warnings():
    data = {
        "name": "my-marketplace",
        "owner": {"name": "Me"},
        "metadata": {"description": "A test marketplace"},
        "plugins": [{"name": "local-plugin", "source": "./plugins/local"}],
    }
    result = validate_marketplace(data)
    assert result.valid
    assert result.warnings == []
    assert result.errors == []


def test_marketplace_npm_source_warning():
    data = {
        "name": "m",
        "owner": {"name": "Me"},
        "plugins": [{"name": "npm-plugin", "source": {"source": "npm", "package": "@x/plugin"}}],
    }
    result = validate_marketplace(data)
    assert result.valid
    npm_warnings = [i for i in result.warnings if "npm" in i.message]
    assert len(npm_warnings) == 1
    assert npm_warnings[0].path == "plugins[0].source"
    assert "npm source which is not yet fully implemented" in npm_warnings[0].message


def test_marketplace_pip_source_warning():
    data = {
        "name": "m",
        "owner": {"name": "Me"},
        "plugins": [{"name": "pip-plugin", "source": {"source": "pip", "package": "x-plugin"}}],
    }
    result = validate_marketplace(data)
    assert result.valid
    pip_warnings = [i for i in result.warnings if "pip" in i.message]
    assert len(pip_warnings) == 1
    assert "pip source which is not yet fully implemented" in pip_warnings[0].message


def test_marketplace_no_description_warning():
    data = {
        "name": "m",
        "owner": {"name": "Me"},
        "plugins": [],
    }
    result = validate_marketplace(data)
    assert result.valid
    desc_warnings = [i for i in result.warnings if "description" in i.path]
    assert len(desc_warnings) == 1
    assert desc_warnings[0].path == "metadata.description"
    assert "No marketplace description" in desc_warnings[0].message


def test_marketplace_empty_plugins_warning():
    data = {
        "name": "m",
        "owner": {"name": "Me"},
        "metadata": {"description": "Has description"},
        "plugins": [],
    }
    result = validate_marketplace(data)
    assert result.valid
    empty_warnings = [i for i in result.warnings if "no plugins" in i.message.lower()]
    assert len(empty_warnings) == 1


def test_marketplace_duplicate_plugin_names_error():
    data = {
        "name": "m",
        "owner": {"name": "Me"},
        "plugins": [
            {"name": "dup", "source": "./p1"},
            {"name": "dup", "source": "./p2"},
        ],
    }
    result = validate_marketplace(data)
    assert not result.valid
    dup_errors = [i for i in result.errors if "Duplicate" in i.message]
    assert len(dup_errors) == 1
    assert dup_errors[0].message == 'Duplicate plugin name "dup" found in marketplace'


def test_marketplace_path_traversal_error():
    data = {
        "name": "m",
        "owner": {"name": "Me"},
        "plugins": [{"name": "bad", "source": "../other-plugin"}],
    }
    result = validate_marketplace(data)
    assert not result.valid
    path_errors = [i for i in result.errors if "Path traversal" in i.message]
    assert len(path_errors) == 1
    assert path_errors[0].path == "plugins[0].source"


def test_marketplace_reserved_name_error():
    data = {
        "name": "claude-code-plugins",
        "owner": {"name": "Me"},
        "plugins": [],
    }
    result = validate_marketplace(data)
    assert not result.valid
    reserved_errors = [i for i in result.errors if "reserved" in i.message]
    assert len(reserved_errors) == 1
    assert "claude-code-plugins" in reserved_errors[0].message


def test_marketplace_missing_name_error():
    result = validate_marketplace({"owner": {"name": "Me"}, "plugins": []})
    assert not result.valid
    assert any(i.path == "name" and "Required" in i.message for i in result.errors)


def test_marketplace_missing_owner_error():
    result = validate_marketplace({"name": "m", "plugins": []})
    assert not result.valid
    assert any(i.path == "owner" and "Required" in i.message for i in result.errors)


def test_marketplace_missing_plugins_error():
    result = validate_marketplace({"name": "m", "owner": {"name": "Me"}})
    assert not result.valid
    assert any(i.path == "plugins" and "Required" in i.message for i in result.errors)


def test_plugin_valid():
    data = {"name": "example-plugin", "version": "1.2.0", "description": "An example"}
    result = validate_plugin(data)
    assert result.valid
    assert result.issues == []


def test_plugin_missing_name_error():
    result = validate_plugin({})
    assert not result.valid
    assert any(i.path == "name" and "Required" in i.message for i in result.errors)


def test_validate_plugin_file():
    path = FIXTURE_ROOT / "plugin" / ".claude-plugin" / "plugin.json"
    result = validate_plugin_file(path)
    assert result.valid
    assert result.issues == []


def test_validate_marketplace_file():
    path = FIXTURE_ROOT / "marketplace" / ".claude-plugin" / "marketplace.json"
    result = validate_marketplace_file(path)
    assert result.valid
    # Fixture has npm and pip plugins so we get those warnings
    assert len(result.warnings) >= 2


def test_validation_result_properties():
    issues = [
        ValidationIssue("error", "name", "name: Required"),
        ValidationIssue("warning", "metadata.description", "No description"),
    ]
    result = ValidationResult(issues=issues)
    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0].level == "error"
    assert len(result.warnings) == 1
    assert result.warnings[0].level == "warning"

    result2 = ValidationResult(issues=[ValidationIssue("warning", "x", "msg")])
    assert result2.valid is True
    assert result2.errors == []
    assert len(result2.warnings) == 1
