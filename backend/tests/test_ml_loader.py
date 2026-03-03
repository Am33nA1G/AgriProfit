"""Unit tests for ML model loader (plan 04-03).

Tests the LRU cache-based lazy model loading.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Test 1: Missing artifact returns None
# ---------------------------------------------------------------------------

def test_missing_artifact_returns_none(tmp_path):
    """get_or_load_model returns None when no .joblib file exists."""
    from app.ml.loader import get_or_load_model

    with patch("app.ml.loader.ARTIFACTS_DIR", tmp_path):
        result = get_or_load_model("nonexistent_commodity")
    assert result is None


# ---------------------------------------------------------------------------
# Test 2: Lazy load on first request, cache hit on second
# ---------------------------------------------------------------------------

def test_lazy_load_on_first_request(tmp_path):
    """First call loads from disk; second call returns cached without reload."""
    from app.ml.loader import get_or_load_model, _model_cache

    # Clear cache state
    _model_cache.clear()

    sentinel = object()
    artifact_path = tmp_path / "wheat.joblib"
    artifact_path.write_bytes(b"fake")

    with patch("app.ml.loader.ARTIFACTS_DIR", tmp_path), \
         patch("app.ml.loader.joblib") as mock_joblib:
        mock_joblib.load.return_value = sentinel

        # First call — should trigger joblib.load
        result1 = get_or_load_model("wheat")
        assert result1 is sentinel
        assert mock_joblib.load.call_count == 1

        # Second call — should be cache hit, no extra load
        result2 = get_or_load_model("wheat")
        assert result2 is sentinel
        assert mock_joblib.load.call_count == 1  # Still 1

    _model_cache.clear()


# ---------------------------------------------------------------------------
# Test 3: LRU eviction when maxsize exceeded
# ---------------------------------------------------------------------------

def test_lru_eviction(tmp_path):
    """With maxsize=2, loading 3 models evicts the oldest one."""
    from cachetools import LRUCache
    from app.ml import loader

    # Temporarily set a small cache
    original_cache = loader._model_cache
    loader._model_cache = LRUCache(maxsize=2)

    try:
        for name in ["a", "b", "c"]:
            (tmp_path / f"{name}.joblib").write_bytes(b"fake")

        with patch.object(loader, "ARTIFACTS_DIR", tmp_path), \
             patch.object(loader, "joblib") as mock_joblib:
            mock_joblib.load.side_effect = lambda p: f"model_{Path(p).stem}"

            # Load A, B, C — A should be evicted
            loader.get_or_load_model("a")
            loader.get_or_load_model("b")
            loader.get_or_load_model("c")

            assert mock_joblib.load.call_count == 3

            # A was evicted — loading again should trigger another load
            loader.get_or_load_model("a")
            assert mock_joblib.load.call_count == 4

    finally:
        loader._model_cache = original_cache
