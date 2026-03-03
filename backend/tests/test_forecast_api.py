"""Integration tests for forecast API endpoint (plan 04-04).

Tests the /api/v1/forecast/{commodity}/{district} endpoint.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.forecast.schemas import ForecastResponse


# Helper: create a mock ForecastResponse
def _make_forecast_response(**overrides) -> ForecastResponse:
    defaults = {
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
    defaults.update(overrides)
    return ForecastResponse(**defaults)


# ---------------------------------------------------------------------------
# Test 1: Forecast endpoint is registered and returns 200
# ---------------------------------------------------------------------------

def test_endpoint_registered(client):
    """GET /api/v1/forecast/Wheat/Pune returns HTTP 200."""
    mock_response = _make_forecast_response()

    with patch("app.forecast.routes.ForecastService") as MockService:
        MockService.return_value.get_forecast.return_value = mock_response
        resp = client.get("/api/v1/forecast/Wheat/Pune")

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2: Response body has all required fields
# ---------------------------------------------------------------------------

def test_forecast_endpoint_14day(client):
    """Response contains the full ForecastResponse schema fields."""
    mock_response = _make_forecast_response()

    with patch("app.forecast.routes.ForecastService") as MockService:
        MockService.return_value.get_forecast.return_value = mock_response
        resp = client.get("/api/v1/forecast/Wheat/Pune?horizon=14")

    body = resp.json()
    assert "direction" in body
    assert "price_low" in body
    assert "price_mid" in body
    assert "price_high" in body
    assert "confidence_colour" in body
    assert "tier_label" in body
    assert "last_data_date" in body
    assert "horizon_days" in body


# ---------------------------------------------------------------------------
# Test 3: Cache hit returns same payload
# ---------------------------------------------------------------------------

def test_cache_hit_returns_same_payload(client):
    """Two calls with same commodity/district return identical payloads."""
    mock_response = _make_forecast_response()

    with patch("app.forecast.routes.ForecastService") as MockService:
        MockService.return_value.get_forecast.return_value = mock_response

        resp1 = client.get("/api/v1/forecast/Wheat/Pune")
        resp2 = client.get("/api/v1/forecast/Wheat/Pune")

    assert resp1.json()["direction"] == resp2.json()["direction"]
    assert resp1.json()["tier_label"] == resp2.json()["tier_label"]


# ---------------------------------------------------------------------------
# Test 4: Low-coverage district returns seasonal fallback
# ---------------------------------------------------------------------------

def test_low_coverage_district_returns_fallback(client):
    """Districts with < 365 days return tier_label='seasonal average fallback'."""
    mock_response = _make_forecast_response(
        commodity="Wheat",
        district="SmallVillage",
        direction="flat",
        price_low=None,
        price_mid=None,
        price_high=None,
        confidence_colour="Red",
        tier_label="seasonal average fallback",
        coverage_message="Insufficient price history for SmallVillage. Showing seasonal averages.",
    )

    with patch("app.forecast.routes.ForecastService") as MockService:
        MockService.return_value.get_forecast.return_value = mock_response
        resp = client.get("/api/v1/forecast/Wheat/SmallVillage")

    body = resp.json()
    assert body["tier_label"] == "seasonal average fallback"
    assert body["direction"] == "flat"
