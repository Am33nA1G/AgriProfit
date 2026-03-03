"""
Unit tests for the arbitrage service (get_arbitrage_results).

These tests use MagicMock for the DB session and patch compare_mandis()
to control MandiComparison fixtures — no real DB required.

TDD Phase: Tests written first (RED). Will pass GREEN after service.py is created.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.arbitrage.schemas import ArbitrageResult, ArbitrageResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mandi_comparison(
    name: str = "Test Mandi",
    district: str = "Ernakulam",
    state: str = "Kerala",
    distance_km: float = 100.0,
    travel_time_hours: float = 4.0,
    is_interstate: bool = False,
    price_per_kg: float = 30.0,
    gross_revenue: float = 3000.0,   # price_per_kg * 100 kg
    net_profit: float = 500.0,
    profit_per_kg: float = 5.0,
    spoilage_percent: float = 1.5,
    verdict: str = "good",
    latest_price_date: date | None = None,
    total_cost: float = 2500.0,
):
    """Build a minimal MandiComparison mock with all fields needed by arbitrage service."""
    from app.transport.schemas import MandiComparison, CostBreakdown, VehicleType, StressTestResult

    costs = CostBreakdown(
        transport_cost=1500.0,
        toll_cost=200.0,
        loading_cost=50.0,
        unloading_cost=50.0,
        mandi_fee=45.0,
        commission=75.0,
        additional_cost=200.0,
        total_cost=total_cost,
    )
    stress = StressTestResult(
        worst_case_profit=100.0,
        break_even_price_per_kg=25.0,
        margin_of_safety_pct=5.0,
        verdict_survives_stress=True,
    )
    return MandiComparison(
        mandi_id=None,
        mandi_name=name,
        district=district,
        state=state,
        distance_km=distance_km,
        price_per_kg=price_per_kg,
        gross_revenue=gross_revenue,
        costs=costs,
        net_profit=net_profit,
        profit_per_kg=profit_per_kg,
        roi_percentage=20.0,
        vehicle_type=VehicleType.TEMPO,
        vehicle_capacity_kg=2000,
        trips_required=1,
        travel_time_hours=travel_time_hours,
        is_interstate=is_interstate,
        spoilage_percent=spoilage_percent,
        verdict=verdict,
        verdict_reason="Worth the trip",
        latest_price_date=latest_price_date,
        stress_test=stress,
    )


# ---------------------------------------------------------------------------
# Schema validation tests (no service needed)
# ---------------------------------------------------------------------------

class TestArbitrageSchemas:
    def test_arbitrage_result_rejects_missing_required_fields(self):
        """ArbitrageResult requires all fields except stale_warning."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ArbitrageResult(
                mandi_name="Test",
                # Missing district, state, distance_km, etc.
            )

    def test_arbitrage_response_with_empty_results_is_valid(self):
        """ArbitrageResponse with results=[] is valid (all suppressed case)."""
        resp = ArbitrageResponse(
            commodity="Wheat",
            origin_district="Ernakulam",
            results=[],
            suppressed_count=5,
            threshold_pct=10.0,
            data_reference_date=date(2025, 10, 30),
            has_stale_data=False,
        )
        assert resp.results == []
        assert resp.suppressed_count == 5

    def test_stale_flag_is_true_when_days_since_update_gt_7(self):
        """is_stale=True when days_since_update > 7."""
        result = ArbitrageResult(
            mandi_name="OldMandi",
            district="Palakkad",
            state="Kerala",
            distance_km=150.0,
            travel_time_hours=5.0,
            is_interstate=False,
            freight_cost_per_quintal=2500.0,
            spoilage_percent=2.0,
            net_profit_per_quintal=300.0,
            verdict="marginal",
            price_date=date(2025, 10, 20),
            days_since_update=10,
            is_stale=True,
            stale_warning="Data last updated 2025-10-20 — signal may be outdated",
        )
        assert result.is_stale is True
        assert result.stale_warning is not None

    def test_stale_flag_is_false_when_days_since_update_lte_7(self):
        """is_stale=False when days_since_update <= 7."""
        result = ArbitrageResult(
            mandi_name="FreshMandi",
            district="Thrissur",
            state="Kerala",
            distance_km=80.0,
            travel_time_hours=3.0,
            is_interstate=False,
            freight_cost_per_quintal=2000.0,
            spoilage_percent=1.0,
            net_profit_per_quintal=600.0,
            verdict="good",
            price_date=date(2025, 10, 28),
            days_since_update=2,
            is_stale=False,
            stale_warning=None,
        )
        assert result.is_stale is False
        assert result.stale_warning is None


# ---------------------------------------------------------------------------
# Service tests (require get_arbitrage_results — will FAIL until Task 2)
# ---------------------------------------------------------------------------

class TestArbitrageService:
    """Tests that require get_arbitrage_results() from app.arbitrage.service."""

    def test_returns_top_3_ranked(self):
        """Service returns at most 3 results sorted by net_profit_per_quintal descending."""
        from app.arbitrage.service import get_arbitrage_results

        ref_date = date(2025, 10, 30)
        mandis = [
            _make_mandi_comparison(
                name=f"Mandi{i}",
                profit_per_kg=float(i * 2),   # 2, 4, 6, 8, 10
                gross_revenue=3000.0,
                net_profit=float(i * 200),    # 200, 400, 600, 800, 1000
                latest_price_date=ref_date,
            )
            for i in range(1, 6)
        ]

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=(mandis, False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        assert len(result.results) <= 3
        # Top 3 by net_profit_per_quintal descending
        profits = [r.net_profit_per_quintal for r in result.results]
        assert profits == sorted(profits, reverse=True)

    def test_margin_threshold_filters_results(self):
        """Mandis with margin < threshold_pct are suppressed; suppressed_count counts them."""
        from app.arbitrage.service import get_arbitrage_results

        ref_date = date(2025, 10, 30)
        # Mandi A: 5% margin → suppressed (below 10% threshold)
        mandi_low = _make_mandi_comparison(
            name="LowMarginMandi",
            gross_revenue=3000.0,
            net_profit=150.0,   # 150/3000 = 5%
            profit_per_kg=1.5,
            latest_price_date=ref_date,
        )
        # Mandi B: 15% margin → passes
        mandi_high = _make_mandi_comparison(
            name="HighMarginMandi",
            gross_revenue=3000.0,
            net_profit=450.0,   # 450/3000 = 15%
            profit_per_kg=4.5,
            latest_price_date=ref_date,
        )

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=([mandi_low, mandi_high], False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        assert result.suppressed_count == 1
        assert len(result.results) == 1
        assert result.results[0].mandi_name == "HighMarginMandi"

    def test_all_suppressed_returns_empty(self):
        """When all mandis are below threshold, results=[] and suppressed_count reflects total."""
        from app.arbitrage.service import get_arbitrage_results

        ref_date = date(2025, 10, 30)
        mandis = [
            _make_mandi_comparison(
                name=f"Mandi{i}",
                gross_revenue=3000.0,
                net_profit=100.0,   # ~3.3% — below 10% threshold
                profit_per_kg=1.0,
                latest_price_date=ref_date,
            )
            for i in range(3)
        ]

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=(mandis, False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        assert result.results == []
        assert result.suppressed_count == 3

    def test_7day_freshness_gate(self):
        """Mandis with price older than (max_date - 7 days) get is_stale=True.

        FreshMandi has the latest price date (ref_date = max of all dates).
        StaleMandi is 10 days before ref_date — strictly older than 7-day window.
        """
        from app.arbitrage.service import get_arbitrage_results

        ref_date = date(2025, 10, 30)   # This is the max date — FreshMandi's date
        stale_date = ref_date - timedelta(days=10)  # 10 days old relative to ref — stale

        mandis = [
            _make_mandi_comparison(
                name="FreshMandi",
                gross_revenue=3000.0,
                net_profit=600.0,   # 20% margin
                profit_per_kg=6.0,
                latest_price_date=ref_date,    # Most recent — becomes data_reference_date
            ),
            _make_mandi_comparison(
                name="StaleMandi",
                gross_revenue=3000.0,
                net_profit=500.0,   # 16.7% margin
                profit_per_kg=5.0,
                latest_price_date=stale_date,  # 10 days before ref — is_stale=True
            ),
        ]

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=(mandis, False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        result_map = {r.mandi_name: r for r in result.results}
        assert result_map["FreshMandi"].is_stale is False
        assert result_map["StaleMandi"].is_stale is True

    def test_stale_results_have_warning(self):
        """Stale results have a non-None stale_warning containing the price date.

        Two mandis: one fresh (sets reference date), one stale (12 days before ref).
        The stale mandi must appear in results with is_stale=True and stale_warning set.
        """
        from app.arbitrage.service import get_arbitrage_results

        ref_date = date(2025, 10, 30)
        stale_date = date(2025, 10, 18)  # 12 days before ref — is_stale=True

        mandis = [
            # Fresh mandi — sets the reference date (max of known dates)
            _make_mandi_comparison(
                name="FreshAnchorMandi",
                gross_revenue=3000.0,
                net_profit=700.0,  # 23.3% margin — above threshold
                profit_per_kg=7.0,
                latest_price_date=ref_date,
            ),
            # Stale mandi — 12 days before ref date
            _make_mandi_comparison(
                name="StaleMandi",
                gross_revenue=3000.0,
                net_profit=600.0,  # 20% margin — above threshold
                profit_per_kg=6.0,
                latest_price_date=stale_date,
            ),
        ]

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=(mandis, False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        stale_results = [r for r in result.results if r.mandi_name == "StaleMandi"]
        assert len(stale_results) == 1
        r = stale_results[0]
        assert r.is_stale is True
        assert r.stale_warning is not None
        assert "2025-10-18" in r.stale_warning

    def test_reference_date_is_max_price_date(self):
        """data_reference_date in response equals max(latest_price_date) across all mandis."""
        from app.arbitrage.service import get_arbitrage_results

        dates = [date(2025, 10, 25), date(2025, 10, 30), date(2025, 10, 20)]
        mandis = [
            _make_mandi_comparison(
                name=f"Mandi{i}",
                gross_revenue=3000.0,
                net_profit=600.0,
                profit_per_kg=6.0,
                latest_price_date=d,
            )
            for i, d in enumerate(dates)
        ]

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=(mandis, False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        assert result.data_reference_date == date(2025, 10, 30)

    def test_result_fields_complete(self):
        """Every ArbitrageResult has all 5 ARB-04 required fields populated."""
        from app.arbitrage.service import get_arbitrage_results

        ref_date = date(2025, 10, 30)
        mandi = _make_mandi_comparison(
            gross_revenue=3000.0,
            net_profit=600.0,
            profit_per_kg=6.0,
            distance_km=120.0,
            travel_time_hours=4.5,
            spoilage_percent=2.0,
            latest_price_date=ref_date,
        )

        db = MagicMock()
        with patch("app.arbitrage.service.compare_mandis", return_value=([mandi], False)):
            result = get_arbitrage_results("Wheat", "Ernakulam", db)

        assert len(result.results) == 1
        r = result.results[0]
        assert r.distance_km > 0
        assert r.travel_time_hours > 0
        assert r.freight_cost_per_quintal > 0
        assert r.spoilage_percent >= 0
        assert isinstance(r.net_profit_per_quintal, float)
