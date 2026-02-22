from __future__ import annotations

import re

from ..errors import FetchError
from ..models.marketplace import (
    GitHubSource,
    HTTPSource,
    MarketplaceManifest,
    URLSource,
)
from ._git import fetch_via_git, github_url
from ._http import fetch_via_http

# Matches "owner/repo" or "owner/repo-name" GitHub shorthand
_GITHUB_SHORTHAND = re.compile(r"^[\w.-]+/[\w.-]+$")


def fetch_marketplace(
    source: str | GitHubSource | URLSource | HTTPSource,
) -> MarketplaceManifest:
    """Fetch a marketplace manifest from a remote source.

    Args:
        source: Where to fetch from. If a string, auto-detected:
            - "owner/repo" → clone from github.com
            - ends with ".git" → clone from that URL
            - otherwise → HTTP GET to the URL (marketplace.json).
            Or pass a GitHubSource, URLSource, or HTTPSource explicitly.

    Returns:
        Parsed marketplace manifest.

    Raises:
        FetchError: On network failure, clone failure, or invalid response.
    """
    if isinstance(source, str):
        source = _detect(source)

    if isinstance(source, GitHubSource):
        return fetch_via_git(github_url(source.repo), ref=source.ref, sha=source.sha)
    if isinstance(source, URLSource):
        return fetch_via_git(source.url, ref=source.ref, sha=source.sha)
    if isinstance(source, HTTPSource):
        return fetch_via_http(source.url)

    raise FetchError(f"Unsupported source type: {type(source)}")


def _detect(s: str) -> GitHubSource | URLSource | HTTPSource:
    if s.endswith(".git"):
        return URLSource(source="url", url=s)
    if _GITHUB_SHORTHAND.match(s):
        return GitHubSource(source="github", repo=s)
    return HTTPSource(source="http", url=s)
