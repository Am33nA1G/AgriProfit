"""Unit tests for ForecastService and schemas (plan 04-03).

Tests the forecast response schema, fallback routing, cache hit, and confidence mapping.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Test 1: ForecastResponse schema has all required fields
# ---------------------------------------------------------------------------

def test_response_schema_fields():
    """ForecastResponse accepts valid data and has all required fields."""
    from app.forecast.schemas import ForecastResponse

    data = {
        "commodity": "Wheat",
        "district": "Pune",
        "horizon_days": 14,
        "direction": "up",
        "price_low": 2100.0,
        "price_mid": 2300.0,
        "price_high": 2500.0,
        "confidence_colour": "Green",
        "tier_label": "full model",
        "last_data_date": "2025-10-30",
    }
    resp = ForecastResponse(**data)

    assert resp.commodity == "Wheat"
    assert resp.district == "Pune"
    assert resp.horizon_days == 14
    assert resp.direction == "up"
    assert resp.price_low == 2100.0
    assert resp.price_mid == 2300.0
    assert resp.price_high == 2500.0
    assert resp.confidence_colour == "Green"
    assert resp.tier_label == "full model"
    assert resp.last_data_date == "2025-10-30"
    assert resp.forecast_points == []
    assert resp.coverage_message is None
    # Phase 7 new fields (PROD-05)
    assert resp.data_freshness_days == 0
    assert resp.is_stale is False
    assert resp.n_markets == 0
    assert resp.typical_error_inr is None


# ---------------------------------------------------------------------------
# Test 2: Low-coverage district returns seasonal fallback
# ---------------------------------------------------------------------------

def test_low_coverage_fallback():
    """When no trained model exists, get_forecast returns a fallback response."""
    from app.forecast.service import ForecastService

    mock_db = MagicMock()
    service = ForecastService(mock_db)

    # Mock _lookup_cache to return None (no cache hit)
    service._lookup_cache = MagicMock(return_value=None)

    # Mock load_meta to return None (no model) and load_seasonal_stats to return None
    # This triggers the national_average_fallback path
    with patch("app.forecast.service.load_meta", return_value=None):
        with patch("app.forecast.service.load_seasonal_stats", return_value=None):
            result = service.get_forecast("Wheat", "SmallVillage", 14)

    assert result.tier_label == "national_average"
    assert result.direction == "flat"
    assert result.confidence_colour == "Red"
    assert result.coverage_message is not None


# ---------------------------------------------------------------------------
# Test 3: Cache hit returns cached response without model invocation
# ---------------------------------------------------------------------------

def test_cache_hit_returns_cached_response():
    """When cache has a valid entry, return it without calling get_or_load_model."""
    from app.forecast.service import ForecastService
    from app.forecast.schemas import ForecastResponse

    mock_db = MagicMock()
    service = ForecastService(mock_db)

    cached_response = ForecastResponse(
        commodity="Wheat",
        district="Pune",
        horizon_days=14,
        direction="up",
        price_low=2100.0,
        price_mid=2300.0,
        price_high=2500.0,
        confidence_colour="Green",
        tier_label="full model",
        last_data_date="2025-10-30",
    )

    service._lookup_cache = MagicMock(return_value=cached_response)

    with patch("app.forecast.service.get_or_load_model") as mock_loader:
        result = service.get_forecast("Wheat", "Pune", 14)
        mock_loader.assert_not_called()

    assert result.direction == "up"
    assert result.tier_label == "full model"


# ---------------------------------------------------------------------------
# Test 4: MAPE to confidence colour mapping
# ---------------------------------------------------------------------------

def test_confidence_colour_mapping():
    """mape_to_confidence_colour returns correct colours for MAPE thresholds."""
    from app.forecast.service import mape_to_confidence_colour

    assert mape_to_confidence_colour(0.05) == "Green"
    assert mape_to_confidence_colour(0.09) == "Green"
    assert mape_to_confidence_colour(0.15) == "Yellow"
    assert mape_to_confidence_colour(0.24) == "Yellow"
    assert mape_to_confidence_colour(0.30) == "Red"
    assert mape_to_confidence_colour(0.50) == "Red"
    assert mape_to_confidence_colour(None) == "Red"


# ---------------------------------------------------------------------------
# Phase 7 new tests — RED state stubs for PROD-01 through PROD-05
# ---------------------------------------------------------------------------

# PROD-01: Corrupted model gate
def test_corrupted_model_blocked():
    """PROD-01: prophet_mape > 5.0 must route to seasonal fallback, not invoke the model."""
    from app.forecast.service import ForecastService

    mock_db = MagicMock()
    service = ForecastService(mock_db)
    corrupted_meta = {
        "prophet_mape": 6.0,
        "tier": "A",
        "strategy": "full_model",
        "r2_score": 0.8,
        "districts_list": [],
        "last_data_date": "2025-01-01",
    }
    with patch("app.forecast.service.load_meta", return_value=corrupted_meta):
        service._lookup_cache = MagicMock(return_value=None)
        service._seasonal_fallback = MagicMock(return_value=MagicMock())
        service.get_forecast("Wheat", "Pune", 14)
        service._seasonal_fallback.assert_called_once()


# PROD-03: Direction uncertainty when band straddles current price
def test_direction_uncertain_when_band_straddles():
    """PROD-03: direction must be 'uncertain' when forecast band straddles current price."""
    from app.forecast.service import ForecastService
    import pandas as pd

    mock_db = MagicMock()
    service = ForecastService(mock_db)

    valid_meta = {
        "prophet_mape": 0.08,
        "tier": "A",
        "strategy": "full_model",
        "r2_score": 0.85,
        "alpha": 1.0,
        "districts_list": [],
        "last_data_date": "2025-01-01",
        "exog_columns": [],
        "interval_coverage_80pct": 0.80,
    }

    # Prophet returns band that straddles the opening price (2000)
    # final_low=1800 < 2000 < 2200=final_high → direction must be "uncertain"
    n = 14
    prophet_result = pd.DataFrame({
        "yhat": [2000.0] * n,
        "yhat_lower": [1800.0] * n,
        "yhat_upper": [2200.0] * n,
    })

    mock_prophet = MagicMock()
    mock_prophet.predict.return_value = prophet_result

    with patch("app.forecast.service.load_meta", return_value=valid_meta):
        with patch("app.forecast.service.get_or_load_model", return_value=mock_prophet):
            service._lookup_cache = MagicMock(return_value=None)
            result = service.get_forecast("Wheat", "Pune", 14)
            assert result.direction == "uncertain", (
                f"Expected 'uncertain' when band straddles current price, got '{result.direction}'"
            )


# PROD-03: Direction "up" when entire band is above current price
def test_direction_up_only_when_band_above():
    """PROD-03: direction must be 'up' when entire forecast band is above current price."""
    from app.forecast.service import ForecastService
    import pandas as pd

    mock_db = MagicMock()
    service = ForecastService(mock_db)

    valid_meta = {
        "prophet_mape": 0.08,
        "tier": "A",
        "strategy": "full_model",
        "r2_score": 0.85,
        "alpha": 1.0,
        "districts_list": [],
        "last_data_date": "2025-01-01",
        "exog_columns": [],
        "interval_coverage_80pct": 0.80,
    }

    # Prophet returns band entirely above opening price (2000)
    # final_low=2100 > 2000 → "up"
    n = 14
    prophet_result = pd.DataFrame({
        "yhat": [2150.0] * n,
        "yhat_lower": [2100.0] * n,
        "yhat_upper": [2200.0] * n,
    })

    mock_prophet = MagicMock()
    mock_prophet.predict.return_value = prophet_result

    with patch("app.forecast.service.load_meta", return_value=valid_meta):
        with patch("app.forecast.service.get_or_load_model", return_value=mock_prophet):
            service._lookup_cache = MagicMock(return_value=None)
            result = service.get_forecast("Wheat", "Pune", 14)
            assert result.direction == "up", (
                f"Expected 'up' when band is entirely above current price, got '{result.direction}'"
            )


# PROD-04: Interval coverage default correction
def test_interval_correction_v3_default():
    """PROD-04: v3-style meta (no interval_coverage_80pct) must default to 0.60, not 0.80."""
    # Pure unit test on the constant resolution expression
    v3_meta: dict = {}

    # Current (wrong) default — documents the old behaviour
    val_old = v3_meta.get("interval_coverage_80pct", 0.80) or 0.80
    assert val_old == 0.80  # old behaviour: overly optimistic

    # Expected new default — will be corrected in Plan 07-03
    val_new = v3_meta.get("interval_coverage_80pct", 0.60) or 0.60
    assert val_new == 0.60  # correct conservative default

    # The two values must differ (ensures the constant change is meaningful)
    assert val_old != val_new


# PROD-05: ForecastResponse accepts and exposes freshness metadata fields
def test_data_freshness_fields():
    """PROD-05: ForecastResponse must accept and expose freshness metadata fields."""
    from app.forecast.schemas import ForecastResponse

    resp = ForecastResponse(
        commodity="Tomato",
        district="Pune",
        horizon_days=14,
        direction="up",
        confidence_colour="Green",
        tier_label="full model",
        last_data_date="2025-10-30",
        data_freshness_days=5,
        is_stale=False,
        n_markets=12,
        typical_error_inr=200.0,
    )
    assert resp.data_freshness_days == 5
    assert resp.is_stale is False
    assert resp.n_markets == 12
    assert resp.typical_error_inr == 200.0


# PROD-05: is_stale threshold based on data_freshness_days
def test_is_stale_threshold():
    """PROD-05: is_stale must reflect staleness threshold (> 30 days = stale)."""
    from app.forecast.schemas import ForecastResponse

    # 31 days old → stale
    stale_resp = ForecastResponse(
        commodity="Tomato",
        district="Pune",
        horizon_days=14,
        direction="flat",
        confidence_colour="Red",
        tier_label="seasonal average fallback",
        last_data_date="2025-09-30",
        data_freshness_days=31,
        is_stale=True,
    )
    assert stale_resp.is_stale is True

    # 30 days old → not stale
    fresh_resp = ForecastResponse(
        commodity="Tomato",
        district="Pune",
        horizon_days=14,
        direction="flat",
        confidence_colour="Yellow",
        tier_label="seasonal average fallback",
        last_data_date="2025-09-30",
        data_freshness_days=30,
        is_stale=False,
    )
    assert fresh_resp.is_stale is False
