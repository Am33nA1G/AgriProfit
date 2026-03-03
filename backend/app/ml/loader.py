"""
ML model loader — LRU cache-based lazy loading of serialised forecaster models.

Models are loaded from disk on first request and cached in memory.
Thread-safe for multi-threaded (but not multi-process) serving.

IMPORTANT: Use `def` route handlers (not `async def`) when calling
get_or_load_model() to avoid blocking the event loop.
"""
import threading

import joblib
from pathlib import Path
from cachetools import LRUCache


# Resolve repo root: this file is at backend/app/ml/loader.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"

_lock = threading.Lock()
_model_cache: LRUCache = LRUCache(maxsize=20)


def get_or_load_model(commodity_slug: str):
    """Lazy-load model from cache or disk. Thread-safe.

    Args:
        commodity_slug: Lowercase commodity name (spaces/slashes replaced with _).
                        Must match the filename in ml/artifacts/{slug}.joblib.

    Returns:
        ForecasterRecursiveMultiSeries instance, or None if artifact is missing.
    """
    with _lock:
        if commodity_slug in _model_cache:
            return _model_cache[commodity_slug]

    artifact_path = ARTIFACTS_DIR / f"{commodity_slug}.joblib"
    if not artifact_path.exists():
        return None

    model = joblib.load(artifact_path)
    with _lock:
        _model_cache[commodity_slug] = model
    return model


def get_model_cache() -> LRUCache:
    """Return cache reference for app.state attachment and monitoring."""
    return _model_cache
