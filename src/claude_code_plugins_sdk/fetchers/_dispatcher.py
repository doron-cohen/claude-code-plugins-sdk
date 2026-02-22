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

    Accepts:
    - GitHubSource — clones from github.com/<repo>
    - URLSource — clones from the git URL
    - HTTPSource — HTTP GET to the URL
    - str — auto-detected:
        - "owner/repo" → GitHubSource
        - ends with ".git" → URLSource
        - otherwise → HTTPSource
    """
    if isinstance(source, str):
        source = _detect(source)

    if isinstance(source, GitHubSource):
        return fetch_via_git(
            github_url(source.repo), ref=source.ref, sha=source.sha
        )
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
