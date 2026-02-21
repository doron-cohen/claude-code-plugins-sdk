from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ..errors import LoadError

if TYPE_CHECKING:
    from pathlib import Path
from ..models.marketplace import MarketplaceManifest


def load_marketplace(path: Path) -> MarketplaceManifest:
    """Load and validate a marketplace manifest.

    Accepts either:
    - a path directly to a marketplace.json file
    - a path to a directory containing .claude-plugin/marketplace.json
    """
    resolved = _resolve_marketplace_path(path)
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise LoadError(f"Marketplace file not found: {resolved}", path=resolved) from e
    except json.JSONDecodeError as e:
        raise LoadError(f"Invalid JSON in {resolved}: {e}", path=resolved) from e
    return MarketplaceManifest.model_validate(data)


def _resolve_marketplace_path(path: Path) -> Path:
    if path.is_file():
        return path
    candidate = path / ".claude-plugin" / "marketplace.json"
    if candidate.exists():
        return candidate
    raise LoadError(
        f"No marketplace.json found at {path} or {candidate}",
        path=path,
    )
