from __future__ import annotations

import httpx

from ..errors import FetchError
from ..models.marketplace import MarketplaceManifest


def fetch_via_http(url: str) -> MarketplaceManifest:
    """Fetch and parse a marketplace.json from a direct HTTPS URL."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code} fetching {url}", url=url) from e
    except httpx.HTTPError as e:
        raise FetchError(f"Network error fetching {url}: {e}", url=url) from e

    try:
        data = response.json()
    except Exception as e:
        raise FetchError(f"Invalid JSON at {url}: {e}", url=url) from e

    return MarketplaceManifest.model_validate(data)
