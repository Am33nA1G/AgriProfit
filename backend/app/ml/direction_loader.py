"""Artifact loader for conservative directional advisory models."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import joblib
from cachetools import LRUCache


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR_DIRECTION = REPO_ROOT / "ml" / "artifacts" / "direction"

_lock = threading.Lock()
_direction_cache: LRUCache = LRUCache(maxsize=20)


def _bundle_path(commodity_slug: str) -> Path:
    return ARTIFACTS_DIR_DIRECTION / f"{commodity_slug}_direction.joblib"


def _meta_path(commodity_slug: str) -> Path:
    return ARTIFACTS_DIR_DIRECTION / f"{commodity_slug}_direction_meta.json"


def load_direction_bundle(commodity_slug: str) -> dict | None:
    """Load and cache the model bundle for a commodity."""
    with _lock:
        if commodity_slug in _direction_cache:
            return _direction_cache[commodity_slug]

    path = _bundle_path(commodity_slug)
    if not path.exists():
        return None

    bundle = joblib.load(path)
    with _lock:
        _direction_cache[commodity_slug] = bundle
    return bundle


def load_direction_meta(commodity_slug: str) -> dict | None:
    """Load JSON metadata for a directional advisory model."""
    path = _meta_path(commodity_slug)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_direction_commodities() -> list[str]:
    """Return slugs that have directional advisory metadata."""
    if not ARTIFACTS_DIR_DIRECTION.exists():
        return []
    return sorted(
        p.stem.removesuffix("_direction_meta")
        for p in ARTIFACTS_DIR_DIRECTION.glob("*_direction_meta.json")
    )


def get_direction_cache() -> LRUCache:
    """Expose the underlying LRU cache for app state wiring if needed."""
    return _direction_cache
