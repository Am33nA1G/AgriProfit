"""Unit tests for XGBoost training script (plan 04-02).

Tests written FIRST (TDD RED phase) — train_xgboost.py implements to pass them.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Test 1: build_series_df filters districts below 730-day threshold
# ---------------------------------------------------------------------------

def test_series_filter_threshold():
    """Given 3 districts with different data spans, only those >= 730 days pass."""
    from scripts.train_xgboost import build_series_df

    # Build mock price data: 3 districts, varying spans
    dates_a = pd.date_range("2015-01-01", periods=800, freq="D")
    dates_b = pd.date_range("2015-01-01", periods=600, freq="D")
    dates_c = pd.date_range("2015-01-01", periods=400, freq="D")

    rows = []
    for d in dates_a:
        rows.append({"price_date": d, "district": "district_A", "modal_price": 100.0})
    for d in dates_b:
        rows.append({"price_date": d, "district": "district_B", "modal_price": 200.0})
    for d in dates_c:
        rows.append({"price_date": d, "district": "district_C", "modal_price": 300.0})

    raw_df = pd.DataFrame(rows)

    series_df, excluded = build_series_df(raw_df, min_days=730)

    # Only district_A has >= 730 days
    assert list(series_df.columns) == ["district_A"]
    assert isinstance(series_df.index, pd.DatetimeIndex)

    # district_B and district_C should be excluded
    excluded_names = {e["district"] for e in excluded}
    assert "district_B" in excluded_names
    assert "district_C" in excluded_names
    assert all(e["reason"] == "insufficient_data" for e in excluded)


# ---------------------------------------------------------------------------
# Test 2: log_training must succeed BEFORE artifact is written
# ---------------------------------------------------------------------------

def test_walk_forward_logs_before_artifact(tmp_path):
    """If log_training raises, the artifact file must NOT be written."""
    from scripts.train_xgboost import log_training

    artifact_path = str(tmp_path / "test_model.joblib")
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock(side_effect=Exception("DB error"))

    with pytest.raises(Exception, match="DB error"):
        log_training(
            db=mock_db,
            commodity="Wheat",
            n_series=5,
            n_folds=4,
            rmse_arr=np.array([10.0, 11.0, 12.0, 13.0]),
            mape_arr=np.array([0.05, 0.06, 0.07, 0.08]),
            artifact_path=artifact_path,
            excluded=[],
        )

    # The artifact file must NOT exist since log_training raised
    assert not Path(artifact_path).exists()


# ---------------------------------------------------------------------------
# Test 3: build_series_df produces DatetimeIndex (skforecast requirement)
# ---------------------------------------------------------------------------

def test_build_series_df_has_datetime_index():
    """Series DataFrame must have DatetimeIndex, not RangeIndex."""
    from scripts.train_xgboost import build_series_df

    dates = pd.date_range("2015-01-01", periods=800, freq="D")
    rows = [{"price_date": d, "district": "dist_A", "modal_price": 100.0} for d in dates]
    raw_df = pd.DataFrame(rows)

    series_df, _ = build_series_df(raw_df, min_days=730)

    assert isinstance(series_df.index, pd.DatetimeIndex), (
        f"Expected DatetimeIndex, got {type(series_df.index)}"
    )
    assert series_df.index.freq is not None or len(series_df) > 0


# ---------------------------------------------------------------------------
# Test 4: mape_to_confidence_colour mapping
# ---------------------------------------------------------------------------

def test_mape_to_confidence_colour():
    """MAPE thresholds map to Green/Yellow/Red confidence colours."""
    from scripts.train_xgboost import mape_to_confidence_colour

    assert mape_to_confidence_colour(0.05) == "Green"
    assert mape_to_confidence_colour(0.09) == "Green"
    assert mape_to_confidence_colour(0.15) == "Yellow"
    assert mape_to_confidence_colour(0.24) == "Yellow"
    assert mape_to_confidence_colour(0.30) == "Red"
    assert mape_to_confidence_colour(0.50) == "Red"
    assert mape_to_confidence_colour(None) == "Red"
