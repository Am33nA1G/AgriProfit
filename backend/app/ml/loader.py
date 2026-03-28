"""
ML model loader — LRU cache-based lazy loading of serialised forecaster models.

Models are loaded from disk on first request and cached in memory.
Thread-safe for multi-threaded (but not multi-process) serving.

IMPORTANT: Use `def` route handlers (not `async def`) when calling
get_or_load_model() to avoid blocking the event loop.

Artifact loading order (v4 preferred, v3 fallback):
  ml/artifacts/v4/{slug}_prophet.joblib   (v4 — preferred)
  ml/artifacts/{slug}_prophet.joblib      (v3 — fallback for backward compat)
"""
import json
import threading

import joblib
from pathlib import Path
from cachetools import LRUCache


# Resolve repo root: this file is at backend/app/ml/loader.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR_V4 = ARTIFACTS_DIR / "v4"

_lock = threading.Lock()
_model_cache: LRUCache = LRUCache(maxsize=20)


def _resolve_artifact(slug_with_suffix: str) -> Path | None:
    """Resolve artifact path: prefer v4, fall back to v3."""
    v4_path = ARTIFACTS_DIR_V4 / slug_with_suffix
    v3_path = ARTIFACTS_DIR / slug_with_suffix
    if v4_path.exists():
        return v4_path
    if v3_path.exists():
        return v3_path
    return None


def get_or_load_model(commodity_slug: str):
    """Lazy-load model from cache or disk. Thread-safe.

    Prefers v4 artifacts; falls back to v3 for backward compatibility.

    Args:
        commodity_slug: Lowercase commodity name (spaces/slashes replaced with _).
                        Must match the filename in ml/artifacts/{slug}.joblib.

    Returns:
        ForecasterRecursiveMultiSeries instance, or None if artifact is missing.
    """
    with _lock:
        if commodity_slug in _model_cache:
            return _model_cache[commodity_slug]

    artifact_path = _resolve_artifact(f"{commodity_slug}.joblib")
    if artifact_path is None:
        return None

    model = joblib.load(artifact_path)
    with _lock:
        _model_cache[commodity_slug] = model
    return model


def load_meta(commodity_slug: str) -> dict | None:
    """Load JSON metadata for a trained commodity model.

    Prefers v4 meta; falls back to v3 for backward compatibility.

    Args:
        commodity_slug: Same slug as used for joblib artifacts.

    Returns:
        Parsed dict. None if not found.
    """
    meta_path = _resolve_artifact(f"{commodity_slug}_meta.json")
    if meta_path is None:
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_seasonal_stats(commodity_slug: str) -> dict | None:
    """Load monthly seasonal price statistics JSON.

    Returns dict keyed by month string ("1"–"12"), each with keys:
    mean, median, p10, p25, p75, p90. None if not found.
    """
    seasonal_path = _resolve_artifact(f"{commodity_slug}_seasonal.json")
    if seasonal_path is None:
        return None
    try:
        return json.loads(seasonal_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_commodity_slugs() -> list[str]:
    """Return sorted list of commodity slugs that have trained artifacts.

    Checks v4 directory first, then root artifacts directory.
    A slug is considered available when its _meta.json exists.
    """
    slugs: set[str] = set()

    for p in ARTIFACTS_DIR_V4.glob("*_meta.json"):
        slugs.add(p.stem.removesuffix("_meta"))

    for p in ARTIFACTS_DIR.glob("*_meta.json"):
        slugs.add(p.stem.removesuffix("_meta"))

    return sorted(slugs)


def get_model_cache() -> LRUCache:
    """Return cache reference for app.state attachment and monitoring."""
    return _model_cache
