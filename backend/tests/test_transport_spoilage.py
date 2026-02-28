"""Tests for spoilage.py — Perishability, weight loss, grade discount, hamali."""
import pytest
from app.transport.spoilage import compute_spoilage, compute_hamali, SpoilageResult, HamaliResult, SPOILAGE_RATES


class TestSpoilageDecay:
    def test_vegetable_at_24h_equals_rate(self):
        result = compute_spoilage("Vegetable", round_trip_hours=24.0)
        assert result.spoilage_fraction == pytest.approx(0.03, rel=0.001)

    def test_fruit_at_24h(self):
        result = compute_spoilage("Fruit", round_trip_hours=24.0)
        assert result.spoilage_fraction == pytest.approx(0.05, rel=0.001)

    def test_grain_at_24h(self):
        result = compute_spoilage("Grain", round_trip_hours=24.0)
        assert result.spoilage_fraction == pytest.approx(0.0015, rel=0.01)

    def test_unknown_category_uses_conservative_default(self):
        result = compute_spoilage(None, round_trip_hours=24.0)
        assert result.spoilage_fraction == pytest.approx(0.005, rel=0.01)

    def test_zero_hours_zero_spoilage(self):
        result = compute_spoilage("Vegetable", round_trip_hours=0.0)
        assert result.spoilage_fraction == 0.0

    def test_12h_vegetable_less_than_24h(self):
        r12 = compute_spoilage("Vegetable", round_trip_hours=12.0)
        r24 = compute_spoilage("Vegetable", round_trip_hours=24.0)
        assert r12.spoilage_fraction < r24.spoilage_fraction
        assert r12.spoilage_fraction == pytest.approx(0.0151, abs=0.001)

    def test_auction_underbid_added_when_high_volatility(self):
        result_normal = compute_spoilage("Vegetable", 24.0, volatility_pct=5.0)
        result_volatile = compute_spoilage("Vegetable", 24.0, volatility_pct=10.0)
        diff = result_volatile.grade_discount_fraction - result_normal.grade_discount_fraction
        assert diff == pytest.approx(0.015, rel=0.01)

    def test_net_saleable_quantity_calculation(self):
        result = compute_spoilage("Vegetable", round_trip_hours=24.0)
        net_qty = result.net_saleable_quantity(1000.0)
        expected = 1000 * (1 - result.spoilage_fraction) * (1 - result.weight_loss_fraction)
        assert net_qty == pytest.approx(expected, rel=0.001)


class TestHamali:
    def test_north_india_rates(self):
        result = compute_hamali("Punjab", 10000.0)
        assert result.loading_hamali == pytest.approx(100 * 10, rel=0.01)
        assert result.unloading_hamali == pytest.approx(100 * 12, rel=0.01)

    def test_south_india_rates(self):
        result = compute_hamali("Kerala", 10000.0)
        assert result.loading_hamali == pytest.approx(100 * 18, rel=0.01)
        assert result.unloading_hamali == pytest.approx(100 * 22, rel=0.01)

    def test_maharashtra_rates(self):
        result = compute_hamali("Maharashtra", 10000.0)
        assert result.loading_hamali == pytest.approx(100 * 13, rel=0.01)
        assert result.unloading_hamali == pytest.approx(100 * 16, rel=0.01)

    def test_unknown_state_uses_default(self):
        result = compute_hamali("Atlantis", 10000.0)
        assert result.loading_hamali == pytest.approx(100 * 15, rel=0.01)
