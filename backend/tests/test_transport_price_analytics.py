"""Tests for price_analytics.py — 7-day price volatility, trend, and confidence."""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock
from app.transport.price_analytics import compute_price_analytics, PriceAnalytics


def _mock_db_with_prices(prices: list[float], days_ago: int = 0) -> MagicMock:
    latest_date = date.today() - timedelta(days=days_ago)
    rows = [
        MagicMock(modal_price=p, price_date=latest_date - timedelta(days=i))
        for i, p in enumerate(prices)
    ]
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = rows
    return db


class TestPriceAnalytics:
    def test_stable_prices_low_volatility(self):
        db = _mock_db_with_prices([3000, 3010, 2990, 3005, 2995, 3000, 3002])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert isinstance(result, PriceAnalytics)
        assert result.volatility_pct < 2.0
        assert result.price_trend == "stable"
        assert result.confidence_score >= 80

    def test_rising_trend(self):
        # Latest price (index 0) is highest — so latest > mean*1.03
        db = _mock_db_with_prices([3900, 3750, 3600, 3450, 3300, 3150, 3000])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.price_trend == "rising"

    def test_falling_trend(self):
        # Latest price (index 0) is lowest — so latest < mean*0.97
        db = _mock_db_with_prices([2000, 2100, 2200, 2300, 2400, 2500, 2600])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.price_trend == "falling"

    def test_high_volatility_reduces_confidence(self):
        db = _mock_db_with_prices([1000, 5000, 1000, 5000, 1000, 5000, 1000])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.volatility_pct > 8.0
        assert result.confidence_score <= 80

    def test_stale_price_reduces_confidence(self):
        db = _mock_db_with_prices([3000], days_ago=5)
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.confidence_score <= 85

    def test_thin_mandi_single_record_reduces_confidence(self):
        db = _mock_db_with_prices([3000])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.confidence_score <= 75

    def test_confidence_floor_at_10(self):
        db = _mock_db_with_prices([1000], days_ago=10)
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.confidence_score >= 10

    def test_no_prices_returns_low_confidence_defaults(self):
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = compute_price_analytics("commodity-id", "Empty Mandi", db)
        assert result.confidence_score == 10
        assert result.price_trend == "stable"
        assert result.volatility_pct == 0.0
