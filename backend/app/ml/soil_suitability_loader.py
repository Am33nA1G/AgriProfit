# backend/app/ml/soil_suitability_loader.py
"""
Loader and inference helpers for the soil crop suitability RandomForest model.

Artifact: ml/artifacts/soil_crop_suitability_rf.joblib
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ARTIFACT_PATH = REPO_ROOT / "ml" / "artifacts" / "soil_crop_suitability_rf.joblib"

# Module-level cache: loaded once, reused for all requests
_bundle: dict | None = None

NUTRIENT_MAP = {
    "Nitrogen": "N",
    "Phosphorus": "P",
    "Potassium": "K",
    "Organic Carbon": "OC",
    "Potential Of Hydrogen": "pH",
}


def load_soil_suitability_model() -> dict | None:
    """Load and cache the artifact. Returns None if file does not exist."""
    global _bundle
    if _bundle is not None:
        return _bundle
    if not _ARTIFACT_PATH.exists():
        return None
    _bundle = joblib.load(_ARTIFACT_PATH)
    return _bundle


def profile_to_feature_vector(
    profile: dict,
    state: str,
    bundle: dict,
) -> Optional[np.ndarray]:
    """
    Convert a block soil profile dict to a 1×16 feature matrix.

    Args:
        profile: {"Nitrogen": {"high": 4, "medium": 0, "low": 96}, ...}
        state:   State name (e.g. "ANDHRA PRADESH") — normalised to UPPER internally
        bundle:  Loaded model artifact dict

    Returns:
        np.ndarray of shape (1, 16) or None on failure.
    """
    try:
        state_enc = bundle["state_encoder"].transform([state.strip().upper()])[0]
    except (ValueError, KeyError):
        state_enc = 0  # Unknown state → encode as 0 (safe fallback)

    row: dict[str, float] = {}
    for nutrient, prefix in NUTRIENT_MAP.items():
        nd = profile.get(nutrient, {})
        row[f"{prefix}_high"] = float(nd.get("high", 0))
        row[f"{prefix}_medium"] = float(nd.get("medium", 0))
        row[f"{prefix}_low"] = float(nd.get("low", 0))
    row["state_enc"] = float(state_enc)

    feature_names: list[str] = bundle["feature_names"]
    try:
        vec = np.array([row[f] for f in feature_names], dtype=float).reshape(1, -1)
    except KeyError:
        return None

    return vec


def predict_crop_suitability(
    profile: dict,
    state: str,
    top_n: int = 5,
) -> list[dict] | None:
    """
    Run ML inference and return top-N crop recommendations.

    Returns None when artifact is absent (caller falls back to rule-based system).
    Returns list of dicts: {"crop_name": str, "score": float, "source": "ml"}
    sorted by score descending.
    """
    bundle = load_soil_suitability_model()
    if bundle is None:
        return None

    vec = profile_to_feature_vector(profile, state, bundle)
    if vec is None:
        return None

    model = bundle["model"]
    crop_names: list[str] = bundle["crop_names"]

    # predict_proba returns a list of (n_samples, n_classes) arrays — one per crop.
    # We take index [0][1]: first (only) sample, probability of class=1 (grown).
    # MIN_CROP_DISTRICTS=5 ensures all labels have both classes so shape[1]==2 always.
    # Guard kept for safety: a single-class crop should score 0 (never grown).
    proba_list = model.predict_proba(vec)
    scores: list[float] = []
    for proba in proba_list:
        if proba.shape[1] == 2:
            scores.append(float(proba[0][1]))
        else:
            # Single class seen during training. proba[0][0] = P(that class).
            # We can't know if it was class 0 or 1 without inspecting the estimator,
            # so conservatively score 0 — it will be filtered by the `score > 0` gate.
            scores.append(0.0)

    ranked = sorted(zip(crop_names, scores), key=lambda x: x[1], reverse=True)

    return [
        {
            "crop_name": name.replace("_", " ").title(),
            "score": round(score, 4),
            "source": "ml",
        }
        for name, score in ranked[:top_n]
        if score > 0.0
    ]
