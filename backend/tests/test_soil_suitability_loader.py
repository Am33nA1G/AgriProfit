# backend/tests/test_soil_suitability_loader.py
"""Unit tests for soil_suitability_loader.py."""
import sys
from pathlib import Path
import numpy as np
import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ml.soil_suitability_loader import (
    profile_to_feature_vector,
    predict_crop_suitability,
    NUTRIENT_MAP,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_profile():
    return {
        "cycle": "2023-24",
        "block_name": "TEST BLOCK - 0001",
        "Nitrogen":              {"high": 20, "medium": 30, "low": 50},
        "Phosphorus":            {"high": 81, "medium": 17, "low": 2},
        "Potassium":             {"high": 50, "medium": 40, "low": 10},
        "Organic Carbon":        {"high": 10, "medium": 20, "low": 70},
        "Potential Of Hydrogen": {"high": 30, "medium": 50, "low": 20},
    }


def _make_bundle():
    """Minimal fake artifact — real sklearn RF with 2 crops."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    import numpy as np

    le = LabelEncoder()
    le.fit(["ANDHRA PRADESH", "GUJARAT", "BIHAR"])

    # Train a tiny 2-crop RF on 20 fake rows
    feature_names = [
        "N_high", "N_medium", "N_low",
        "P_high", "P_medium", "P_low",
        "K_high", "K_medium", "K_low",
        "OC_high", "OC_medium", "OC_low",
        "pH_high", "pH_medium", "pH_low",
        "state_enc",
    ]
    X = np.random.RandomState(0).rand(20, 16) * 100
    y = np.column_stack([
        np.array([1, 0] * 10),  # rice
        np.array([0, 1] * 10),  # wheat
    ])
    model = RandomForestClassifier(n_estimators=5, random_state=0)
    model.fit(X, y)

    return {
        "model": model,
        "feature_names": feature_names,
        "crop_names": ["rice", "wheat"],
        "state_encoder": le,
        "train_accuracy": 0.9,
        "n_districts": 20,
        "n_crops": 2,
        "trained_at": "2026-01-01T00:00:00",
    }


# ── profile_to_feature_vector ────────────────────────────────────────────────

def test_profile_to_feature_vector_returns_correct_shape():
    bundle = _make_bundle()
    vec = profile_to_feature_vector(_make_profile(), "ANDHRA PRADESH", bundle)
    assert vec is not None
    assert vec.shape == (1, 16)


def test_profile_to_feature_vector_nitrogen_values():
    bundle = _make_bundle()
    profile = _make_profile()
    vec = profile_to_feature_vector(profile, "ANDHRA PRADESH", bundle)
    feature_names = bundle["feature_names"]
    n_high_idx = feature_names.index("N_high")
    assert vec[0, n_high_idx] == 20.0


def test_profile_to_feature_vector_unknown_state_uses_zero():
    bundle = _make_bundle()
    # "UNKNOWN STATE" not in the encoder → should not raise, uses fallback 0
    vec = profile_to_feature_vector(_make_profile(), "UNKNOWN STATE", bundle)
    assert vec is not None
    state_idx = bundle["feature_names"].index("state_enc")
    assert vec[0, state_idx] == 0.0


def test_profile_to_feature_vector_missing_nutrient_fills_zeros():
    bundle = _make_bundle()
    profile = _make_profile()
    del profile["Potassium"]  # missing nutrient
    vec = profile_to_feature_vector(profile, "GUJARAT", bundle)
    assert vec is not None
    feature_names = bundle["feature_names"]
    for suffix in ["high", "medium", "low"]:
        idx = feature_names.index(f"K_{suffix}")
        assert vec[0, idx] == 0.0


# ── predict_crop_suitability ─────────────────────────────────────────────────

def test_predict_returns_none_when_no_artifact():
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=None):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH")
    assert result is None


def test_predict_returns_list_of_dicts():
    bundle = _make_bundle()
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=bundle):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH")
    assert isinstance(result, list)
    for item in result:
        assert "crop_name" in item
        assert "score" in item
        assert "source" in item
        assert item["source"] == "ml"


def test_predict_respects_top_n():
    bundle = _make_bundle()
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=bundle):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH", top_n=1)
    assert len(result) <= 1


def test_predict_scores_are_descending():
    bundle = _make_bundle()
    with patch("app.ml.soil_suitability_loader.load_soil_suitability_model", return_value=bundle):
        result = predict_crop_suitability(_make_profile(), "ANDHRA PRADESH")
    if len(result) > 1:
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)
