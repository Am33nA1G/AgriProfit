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


# ---------------------------------------------------------------------------
# Test 2: Low-coverage district returns seasonal fallback
# ---------------------------------------------------------------------------

def test_low_coverage_fallback():
    """Districts with < 365 days of data get seasonal fallback, not ML forecast."""
    from app.forecast.service import ForecastService

    mock_db = MagicMock()
    service = ForecastService(mock_db)

    # Mock _lookup_cache to return None (no cache hit)
    service._lookup_cache = MagicMock(return_value=None)
    # Mock _get_coverage_days to return < 365
    service._get_coverage_days = MagicMock(return_value=200)

    result = service.get_forecast("Wheat", "SmallVillage", 14)

    assert result.tier_label == "seasonal average fallback"
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
