from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ..errors import FetchError
from ..loaders.marketplace import load_marketplace

if TYPE_CHECKING:
    from ..models.marketplace import MarketplaceManifest


def fetch_via_git(
    url: str, ref: str | None = None, sha: str | None = None
) -> MarketplaceManifest:
    """Clone a git repo and load its marketplace manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _clone(url, Path(tmpdir), ref=ref)
        if sha:
            _verify_sha(Path(tmpdir), sha, url)
        return load_marketplace(Path(tmpdir))


def github_url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def _clone(url: str, dest: Path, ref: str | None) -> None:
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [url, str(dest)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        raise FetchError(f"git clone timed out for {url}", url=url) from e
    except FileNotFoundError as e:
        raise FetchError("git is not installed or not in PATH", url=url) from e
    if result.returncode != 0:
        raise FetchError(
            f"git clone failed for {url}: {result.stderr.strip()}", url=url
        )


def _verify_sha(repo_dir: Path, expected_sha: str, url: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    actual = result.stdout.strip()
    if not actual.startswith(expected_sha[:7]):
        raise FetchError(
            f"SHA mismatch: expected {expected_sha[:7]}…, got {actual[:7]}…",
            url=url,
        )
