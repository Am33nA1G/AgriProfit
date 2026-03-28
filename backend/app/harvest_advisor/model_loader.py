"""
Yield model loader with LRU cache.

Loading priority for vegetables / fruits:
  1. Per-crop model: yield_rf_vegetable_{crop}.joblib  (trained by train_vegetable_models.py)
  2. Category model: yield_rf_{category}.joblib        (trained by train_yield_model.py)

Per-crop models are preferred because they have lower overfitting and were trained
with tighter hyperparameters (lower max_depth, higher min_samples_leaf).
"""
import threading
import logging
from pathlib import Path
from typing import Optional

import joblib
from cachetools import LRUCache

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"

_lock = threading.Lock()
_yield_cache: LRUCache = LRUCache(maxsize=20)   # bumped from 10 to fit per-crop models

CROP_CATEGORIES = {
    "food_grains": ["rice", "wheat", "maize", "bajra", "jowar", "barley"],
    "pulses": ["arhar", "moong", "urad", "chana", "lentil"],
    "oilseeds": ["groundnut", "mustard", "soybean", "sunflower"],
    "vegetables": ["tomato", "onion", "potato", "brinjal", "cauliflower", "carrot"],
    "fruits": ["mango", "banana", "grapes", "orange", "pomegranate"],
    "cash_crops": ["cotton", "sugarcane", "jute", "coffee"],
}

# Crops that have (or may have) per-crop models
_PER_CROP_ELIGIBLE = frozenset(
    CROP_CATEGORIES["vegetables"] + CROP_CATEGORIES["fruits"]
)


def get_crop_category(crop_name: str) -> Optional[str]:
    """Return the category for a crop, or None if not categorized."""
    name = crop_name.lower()
    for category, crops in CROP_CATEGORIES.items():
        if name in crops:
            return category
    return None


def load_yield_model(crop_category: str, crop_name: Optional[str] = None) -> Optional[dict]:
    """
    Load yield model for a crop.

    For vegetables and fruits, first tries a per-crop model
    (yield_rf_vegetable_{crop_name}.joblib), then falls back to the
    category model (yield_rf_{category}.joblib).

    Args:
        crop_category: Category string, e.g. "vegetables"
        crop_name: Specific crop name, e.g. "tomato". Used for per-crop lookup.
    """
    # ── Try per-crop model first (vegetables and fruits only) ──────────
    if crop_name and crop_name.lower() in _PER_CROP_ELIGIBLE:
        cache_key = f"per_crop_{crop_name.lower()}"
        with _lock:
            if cache_key in _yield_cache:
                return _yield_cache[cache_key]

        per_crop_path = ARTIFACTS_DIR / f"yield_rf_vegetable_{crop_name.lower()}.joblib"
        if per_crop_path.exists():
            try:
                model_dict = joblib.load(per_crop_path)
                with _lock:
                    _yield_cache[cache_key] = model_dict
                logger.debug("Loaded per-crop model for %s", crop_name)
                return model_dict
            except Exception as e:
                logger.warning("Failed to load per-crop model for %s: %s", crop_name, e)

    # ── Fall back to category model ─────────────────────────────────────
    with _lock:
        if crop_category in _yield_cache:
            return _yield_cache[crop_category]

    artifact_path = ARTIFACTS_DIR / f"yield_rf_{crop_category}.joblib"
    if not artifact_path.exists():
        return None

    try:
        model_dict = joblib.load(artifact_path)
        with _lock:
            _yield_cache[crop_category] = model_dict
        return model_dict
    except Exception as e:
        logger.error("Failed to load yield model for %s: %s", crop_category, e)
        return None
