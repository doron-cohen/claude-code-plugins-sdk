import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_code_plugins_sdk.models.marketplace import (
    GitHubSource,
    MarketplaceManifest,
    NPMSource,
    PIPSource,
    PluginEntry,
    URLSource,
)


def test_marketplace_full():
    """Parse the full marketplace fixture."""
    data = json.loads(
        (Path("tests/fixtures/marketplace/.claude-plugin/marketplace.json")).read_text()
    )
    m = MarketplaceManifest.model_validate(data)
    assert m.name == "example-marketplace"
    assert m.owner.name == "Test Author"
    assert len(m.plugins) == 5


def test_marketplace_minimal():
    data = json.loads(
        (Path("tests/fixtures/marketplace/.claude-plugin/minimal-marketplace.json")).read_text()
    )
    m = MarketplaceManifest.model_validate(data)
    assert m.name == "minimal-marketplace"
    assert m.description is None
    assert len(m.plugins) == 1


def test_marketplace_missing_name():
    with pytest.raises(ValidationError):
        MarketplaceManifest.model_validate({"owner": {"name": "Test"}, "plugins": []})


def test_marketplace_missing_owner():
    with pytest.raises(ValidationError):
        MarketplaceManifest.model_validate({"name": "test", "plugins": []})


def test_source_relative_path():
    entry = PluginEntry.model_validate({"name": "p", "source": "./plugins/foo"})
    assert entry.source == "./plugins/foo"
    assert isinstance(entry.source, str)


def test_source_github():
    entry = PluginEntry.model_validate(
        {
            "name": "p",
            "source": {"source": "github", "repo": "owner/repo", "ref": "v1.0", "sha": "abc123"},
        }
    )
    assert isinstance(entry.source, GitHubSource)
    assert entry.source.repo == "owner/repo"


def test_source_url():
    entry = PluginEntry.model_validate(
        {"name": "p", "source": {"source": "url", "url": "https://gitlab.com/x/y.git"}}
    )
    assert isinstance(entry.source, URLSource)


def test_source_npm():
    entry = PluginEntry.model_validate(
        {"name": "p", "source": {"source": "npm", "package": "@example/plugin", "version": "^1.0"}}
    )
    assert isinstance(entry.source, NPMSource)


def test_source_pip():
    entry = PluginEntry.model_validate(
        {"name": "p", "source": {"source": "pip", "package": "my-plugin"}}
    )
    assert isinstance(entry.source, PIPSource)


def test_plugin_entry_defaults():
    entry = PluginEntry.model_validate({"name": "foo", "source": "./x"})
    assert entry.strict is True
    assert entry.tags == []
    assert entry.keywords == []


def test_marketplace_unknown_fields_allowed():
    """Extra fields should not raise an error."""
    m = MarketplaceManifest.model_validate(
        {
            "name": "test",
            "owner": {"name": "Me"},
            "plugins": [],
            "unknownField": "value",
        }
    )
    assert m.name == "test"
