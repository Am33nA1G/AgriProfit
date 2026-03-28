"""
Integration tests for GET /api/v1/arbitrage/{commodity}/{district}.

Uses FastAPI TestClient + monkeypatching of get_arbitrage_results() to avoid
real DB/OSRM calls. Validates HTTP status codes, response shapes, and error
handling.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.arbitrage.schemas import ArbitrageResponse, ArbitrageResult

client = TestClient(app)


def _make_arb_result(
    mandi_name: str = "TestMandi",
    district: str = "Thrissur",
    state: str = "Kerala",
    net_profit_per_quintal: float = 450.0,
    days_since_update: int = 2,
    is_stale: bool = False,
) -> ArbitrageResult:
    return ArbitrageResult(
        mandi_name=mandi_name,
        district=district,
        state=state,
        distance_km=120.0,
        travel_time_hours=4.5,
        is_interstate=False,
        freight_cost_per_quintal=2200.0,
        spoilage_percent=1.5,
        net_profit_per_quintal=net_profit_per_quintal,
        verdict="good",
        price_date=date(2025, 10, 28),
        days_since_update=days_since_update,
        is_stale=is_stale,
        stale_warning=None,
    )


def _make_arb_response(results=None, suppressed_count=0) -> ArbitrageResponse:
    if results is None:
        results = [_make_arb_result()]
    return ArbitrageResponse(
        commodity="Wheat",
        origin_district="Ernakulam",
        results=results,
        suppressed_count=suppressed_count,
        threshold_pct=10.0,
        data_reference_date=date(2025, 10, 30),
        has_stale_data=any(r.is_stale for r in results),
    )


class TestArbitrageAPIEndpoint:
    def test_successful_arbitrage(self):
        """GET /api/v1/arbitrage/Wheat/Ernakulam returns 200 with valid ArbitrageResponse."""
        mock_response = _make_arb_response()

        with patch("app.arbitrage.routes.get_arbitrage_results", return_value=mock_response):
            response = client.get("/api/v1/arbitrage/Wheat/Ernakulam")

        assert response.status_code == 200
        data = response.json()
        assert data["commodity"] == "Wheat"
        assert data["origin_district"] == "Ernakulam"
        assert isinstance(data["results"], list)

    def test_response_has_required_fields(self):
        """Response JSON must contain all ARB-01 through ARB-04 required fields."""
        mock_response = _make_arb_response()

        with patch("app.arbitrage.routes.get_arbitrage_results", return_value=mock_response):
            response = client.get("/api/v1/arbitrage/Wheat/Ernakulam")

        assert response.status_code == 200
        data = response.json()

        # Top-level envelope fields
        assert "results" in data
        assert "suppressed_count" in data
        assert "threshold_pct" in data
        assert "data_reference_date" in data
        assert "has_stale_data" in data
        assert "commodity" in data
        assert "origin_district" in data

        # Per-result fields (ARB-04)
        if data["results"]:
            result = data["results"][0]
            assert "distance_km" in result
            assert "travel_time_hours" in result
            assert "freight_cost_per_quintal" in result
            assert "spoilage_percent" in result
            assert "net_profit_per_quintal" in result

    def test_unknown_commodity_returns_404(self):
        """When commodity is not found, service raises ValueError('not found'), returning 404."""
        with patch(
            "app.arbitrage.routes.get_arbitrage_results",
            side_effect=ValueError("Commodity 'UnknownCrop' not found"),
        ):
            response = client.get("/api/v1/arbitrage/UnknownCrop/Ernakulam")

        assert response.status_code == 404

    def test_invalid_district_returns_400(self):
        """When district coordinates cannot be resolved, service raises ValueError, returning 400."""
        with patch(
            "app.arbitrage.routes.get_arbitrage_results",
            side_effect=ValueError("Could not determine coordinates for district 'ZZZUnknown'"),
        ):
            response = client.get("/api/v1/arbitrage/Wheat/ZZZUnknown")

        assert response.status_code == 400

    def test_max_distance_query_param_accepted(self):
        """max_distance_km query parameter is accepted without validation error."""
        mock_response = _make_arb_response()

        with patch("app.arbitrage.routes.get_arbitrage_results", return_value=mock_response) as mock_fn:
            response = client.get("/api/v1/arbitrage/Wheat/Ernakulam?max_distance_km=300")

        assert response.status_code == 200
        # Verify max_distance_km was passed through to the service
        _, kwargs = mock_fn.call_args
        assert kwargs.get("max_distance_km") == 300.0 or mock_fn.call_args[0][3] == 300.0

    def test_empty_results_with_suppressed_count(self):
        """When all mandis are below threshold, returns 200 with results=[] and suppressed_count > 0."""
        mock_response = _make_arb_response(results=[], suppressed_count=5)

        with patch("app.arbitrage.routes.get_arbitrage_results", return_value=mock_response):
            response = client.get("/api/v1/arbitrage/Wheat/Ernakulam")

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["suppressed_count"] == 5

    def test_stale_data_flag_propagated(self):
        """has_stale_data is True in response when any result is stale."""
        stale_result = _make_arb_result(
            is_stale=True,
            days_since_update=12,
        )
        stale_result.stale_warning = "Data last updated 2025-10-18 — signal may be outdated"
        mock_response = ArbitrageResponse(
            commodity="Wheat",
            origin_district="Ernakulam",
            results=[stale_result],
            suppressed_count=0,
            threshold_pct=10.0,
            data_reference_date=date(2025, 10, 30),
            has_stale_data=True,
        )

        with patch("app.arbitrage.routes.get_arbitrage_results", return_value=mock_response):
            response = client.get("/api/v1/arbitrage/Wheat/Ernakulam")

        assert response.status_code == 200
        data = response.json()
        assert data["has_stale_data"] is True
