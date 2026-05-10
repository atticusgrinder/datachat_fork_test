"""Public changelog endpoint — reads markdown files from changelogs/ directory."""

import os
from pathlib import Path

import frontmatter
from fastapi import APIRouter

router = APIRouter()

# Module-level cache: {filepath: (mtime, parsed_entry)}
_cache: dict[str, tuple[float, dict]] = {}

# changelogs/ lives inside backend/ so it's included in Railway deployments
CHANGELOGS_DIR = Path(__file__).resolve().parents[2] / "changelogs"


def _parse_entry(filepath: Path) -> dict:
    """Parse a changelog markdown file into a dict."""
    post = frontmatter.load(str(filepath))
    slug = filepath.stem
    return {
        "slug": slug,
        "title": post.get("title", slug),
        "date": str(post.get("date", "")),
        "version": post.get("version", ""),
        "tags": post.get("tags", []),
        "body": post.content,
    }


def _get_entries() -> list[dict]:
    """Read all changelog files, using mtime-based cache."""
    if not CHANGELOGS_DIR.is_dir():
        return []

    entries = []
    for filepath in CHANGELOGS_DIR.glob("*.md"):
        mtime = os.path.getmtime(filepath)
        key = str(filepath)
        cached = _cache.get(key)
        if cached and cached[0] == mtime:
            entries.append(cached[1])
        else:
            entry = _parse_entry(filepath)
            _cache[key] = (mtime, entry)
            entries.append(entry)

    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


@router.get("/api/changelog")
async def get_changelog():
    """Return all changelog entries sorted by date descending."""
    return {"entries": _get_entries()}
