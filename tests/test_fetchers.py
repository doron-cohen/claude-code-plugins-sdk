"""Tests for the remote fetcher layer."""

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from claude_code_plugins_sdk import (
    FetchError,
    GitHubSource,
    HTTPSource,
    URLSource,
    fetch_marketplace,
)
from claude_code_plugins_sdk.fetchers._dispatcher import _detect

VALID_MARKETPLACE = {
    "name": "test-marketplace",
    "owner": {"name": "Test"},
    "plugins": [
        {"name": "plugin-a", "source": "./plugins/a"},
    ],
}


def make_git_marketplace(tmp_path: Path, data: dict) -> Path:
    """Create a local git repo with a marketplace.json."""
    repo = tmp_path / "repo"
    repo.mkdir()
    claude_plugin = repo / ".claude-plugin"
    claude_plugin.mkdir()
    (claude_plugin / "marketplace.json").write_text(json.dumps(data))
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "t@t.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "T"],
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        capture_output=True,
        check=True,
    )
    return repo


# --- HTTP fetcher tests ---


def test_fetch_via_http_success(httpx_mock):
    httpx_mock.add_response(json=VALID_MARKETPLACE)
    result = fetch_marketplace(
        HTTPSource(source="http", url="https://example.com/marketplace.json")
    )
    assert result.name == "test-marketplace"
    assert len(result.plugins) == 1
    assert result.plugins[0].name == "plugin-a"


def test_fetch_via_http_404(httpx_mock):
    httpx_mock.add_response(status_code=404)
    with pytest.raises(FetchError):
        fetch_marketplace(
            HTTPSource(source="http", url="https://example.com/marketplace.json")
        )


def test_fetch_via_http_500(httpx_mock):
    httpx_mock.add_response(status_code=500)
    with pytest.raises(FetchError):
        fetch_marketplace(
            HTTPSource(source="http", url="https://example.com/marketplace.json")
        )


def test_fetch_via_http_invalid_json(httpx_mock):
    httpx_mock.add_response(content=b"not json", status_code=200)
    with pytest.raises(FetchError):
        fetch_marketplace(
            HTTPSource(source="http", url="https://example.com/marketplace.json")
        )


def test_fetch_via_http_invalid_schema(httpx_mock):
    httpx_mock.add_response(json={"plugins": []}, status_code=200)
    with pytest.raises(ValidationError):
        fetch_marketplace(
            HTTPSource(source="http", url="https://example.com/marketplace.json")
        )


# --- Git fetcher tests ---


def test_fetch_via_git_local(tmp_path):
    repo = make_git_marketplace(tmp_path, VALID_MARKETPLACE)
    url = f"file://{repo.resolve()}"
    result = fetch_marketplace(URLSource(source="url", url=url))
    assert result.name == "test-marketplace"
    assert len(result.plugins) == 1


def test_fetch_via_git_bad_url():
    with pytest.raises(FetchError):
        fetch_marketplace(
            URLSource(source="url", url="file:///nonexistent/path/that/does/not/exist")
        )


def test_fetch_via_git_invalid_schema(tmp_path):
    repo = make_git_marketplace(tmp_path, {"plugins": []})
    url = f"file://{repo.resolve()}"
    with pytest.raises(ValidationError):
        fetch_marketplace(URLSource(source="url", url=url))


# --- Dispatcher / string auto-detection tests ---


def test_detect_github_shorthand():
    result = _detect("anthropics/claude-code")
    assert isinstance(result, GitHubSource)
    assert result.repo == "anthropics/claude-code"


def test_detect_git_url():
    result = _detect("https://gitlab.com/x/y.git")
    assert isinstance(result, URLSource)
    assert result.url == "https://gitlab.com/x/y.git"


def test_detect_http_url():
    result = _detect("https://example.com/marketplace.json")
    assert isinstance(result, HTTPSource)
    assert result.url == "https://example.com/marketplace.json"


def test_detect_github_with_dash():
    result = _detect("my-org/my-plugin-repo")
    assert isinstance(result, GitHubSource)
    assert result.repo == "my-org/my-plugin-repo"


# --- Integration test ---


@pytest.mark.integration
def test_fetch_anthropic_official_marketplace():
    m = fetch_marketplace("anthropics/claude-code")
    assert m.name == "claude-code-plugins"
    assert len(m.plugins) > 5
