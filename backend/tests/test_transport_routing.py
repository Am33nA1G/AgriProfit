"""Tests for RoutingService — OSRM call, DB cache, fallback behavior."""
import pytest
from unittest.mock import MagicMock, patch
import httpx

from app.transport.routing import RoutingService


@pytest.fixture
def routing():
    return RoutingService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    # Simulate no cache hit by default
    db.query.return_value.filter_by.return_value.first.return_value = None
    return db


class TestRoutingServiceOSRMSuccess:
    def test_osrm_success_returns_distance_and_osrm_source(self, routing, mock_db):
        """OSRM returns valid response → distance_km from response, source='osrm'."""
        osrm_payload = {
            "code": "Ok",
            "routes": [{"distance": 85500.0}],  # 85.5 km
        }
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = osrm_payload
            mock_get.return_value = mock_resp

            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert dist == pytest.approx(85.5, rel=0.01)
        assert source == "osrm"

    def test_osrm_success_writes_to_db_cache(self, routing, mock_db):
        """OSRM success → result persisted to road_distance_cache table."""
        osrm_payload = {"code": "Ok", "routes": [{"distance": 100000.0}]}
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = osrm_payload
            mock_get.return_value = mock_resp

            routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestRoutingServiceFallback:
    def test_osrm_timeout_returns_estimated_source(self, routing, mock_db):
        """OSRM timeout → fallback distance returned, source='estimated'."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert source == "estimated"
        assert dist > 0

    def test_osrm_timeout_does_not_write_to_cache(self, routing, mock_db):
        """Estimated distances must NOT be cached — allow OSRM retry next request."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_after_fallback_next_call_retries_osrm(self, routing, mock_db):
        """After a fallback (no cache write), next call must still hit OSRM, not cache."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        # DB still has no cache entry (add was never called)
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"code": "Ok", "routes": [{"distance": 50000.0}]}
            mock_get.return_value = mock_resp

            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert source == "osrm"
        mock_get.assert_called_once()


class TestRoutingServiceCache:
    def test_cache_hit_returns_without_calling_osrm(self, routing, mock_db):
        """Cache hit → return immediately, never call OSRM."""
        cached = MagicMock()
        cached.distance_km = 120.5
        cached.source = "osrm"
        mock_db.query.return_value.filter_by.return_value.first.return_value = cached

        with patch("httpx.get") as mock_get:
            dist, source = routing.get_distance_km(28.6, 77.2, 30.9, 75.8, mock_db)

        assert dist == 120.5
        assert source == "osrm"
        mock_get.assert_not_called()
