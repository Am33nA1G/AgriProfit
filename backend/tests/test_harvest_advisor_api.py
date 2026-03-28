"""Tests for harvest advisor API endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.harvest_advisor.schemas import HarvestAdvisorResponse


def _make_mock_response() -> HarvestAdvisorResponse:
    return HarvestAdvisorResponse(
        state="Maharashtra",
        district="Nashik",
        season="kharif",
        recommendations=[],
        weather_warnings=[],
        rainfall_deficit_pct=None,
        drought_risk="none",
        soil_data_available=False,
        yield_data_available=False,
        forecast_available=False,
        disclaimer="Test disclaimer",
        generated_at="2026-03-06T00:00:00+00:00",
        coverage_notes=[],
    )


def test_recommend_missing_params(client):
    """Returns 422 when required params missing."""
    resp = client.get("/api/v1/harvest-advisor/recommend")
    assert resp.status_code == 422


def test_recommend_returns_200(client):
    """Returns 200 with valid params (mocked service)."""
    mock_response = _make_mock_response()
    with patch(
        "app.harvest_advisor.routes.HarvestAdvisorService"
    ) as MockService:
        MockService.return_value.compute_recommendation.return_value = mock_response
        resp = client.get(
            "/api/v1/harvest-advisor/recommend",
            params={"state": "Maharashtra", "district": "Nashik", "season": "kharif"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "Maharashtra"
    assert body["district"] == "Nashik"


def test_weather_warnings_missing_params(client):
    """Returns 422 when required params missing."""
    resp = client.get("/api/v1/harvest-advisor/weather-warnings")
    assert resp.status_code == 422


def test_weather_warnings_returns_200(client):
    """Returns 200 with valid params."""
    with patch(
        "app.harvest_advisor.routes.HarvestAdvisorService"
    ) as MockService:
        MockService.return_value.get_weather_warnings.return_value = []
        resp = client.get(
            "/api/v1/harvest-advisor/weather-warnings",
            params={"state": "Maharashtra", "district": "Nashik"},
        )
    assert resp.status_code == 200
    assert resp.json() == []


def test_districts_returns_200(client):
    """Returns 200 for districts endpoint."""
    with patch(
        "app.harvest_advisor.routes.HarvestAdvisorService"
    ) as MockService:
        MockService.return_value.get_districts_with_data.return_value = ["Nashik", "Pune"]
        resp = client.get(
            "/api/v1/harvest-advisor/districts",
            params={"state": "Maharashtra"},
        )
    assert resp.status_code == 200
    assert "Nashik" in resp.json()


def test_districts_missing_state(client):
    """Returns 422 when state param missing."""
    resp = client.get("/api/v1/harvest-advisor/districts")
    assert resp.status_code == 422
