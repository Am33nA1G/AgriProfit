"""Tests for OpenMeteoClient."""
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.harvest_advisor.weather_client import OpenMeteoClient
from app.models.open_meteo_cache import OpenMeteoCache


def test_fetch_forecast_unknown_district(test_db):
    """Returns None for district not in coords."""
    client = OpenMeteoClient()
    with patch("app.harvest_advisor.weather_client._DISTRICT_COORDS", {}):
        result = client.fetch_forecast("UnknownDistrict", "TestState", test_db)
    assert result is None


def test_fetch_forecast_cache_hit(test_db):
    """Returns cached data without making HTTP call."""
    cached_data = {"daily": {"temperature_2m_max": [35, 36, 37]}}
    expires_at = datetime.now(timezone.utc) + timedelta(hours=5)

    # Insert cache row
    row = OpenMeteoCache(
        district="Nashik",
        state="Maharashtra",
        forecast_json=json.dumps(cached_data),
        expires_at=expires_at,
    )
    test_db.add(row)
    test_db.commit()

    client = OpenMeteoClient()
    with patch("httpx.get") as mock_get:
        result = client.fetch_forecast("Nashik", "Maharashtra", test_db)

    # Should not have called httpx.get
    mock_get.assert_not_called()
    assert result == cached_data


def test_fetch_forecast_api_call(test_db):
    """Makes API call when no cache hit and district has coords."""
    mock_response_data = {
        "daily": {
            "time": ["2026-03-06"],
            "temperature_2m_max": [32.5],
            "temperature_2m_min": [18.0],
            "precipitation_sum": [0.0],
        }
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_response_data
    mock_resp.raise_for_status.return_value = None

    client = OpenMeteoClient()
    fake_coords = {"Nashik": [20.0, 73.8]}

    with patch("app.harvest_advisor.weather_client._DISTRICT_COORDS", fake_coords), \
         patch("httpx.get", return_value=mock_resp):
        result = client.fetch_forecast("Nashik", "Maharashtra", test_db)

    assert result == mock_response_data


def test_fetch_forecast_api_failure_returns_none(test_db):
    """Returns None when API call fails."""
    client = OpenMeteoClient()
    fake_coords = {"Nashik": [20.0, 73.8]}

    with patch("app.harvest_advisor.weather_client._DISTRICT_COORDS", fake_coords), \
         patch("httpx.get", side_effect=Exception("network error")):
        result = client.fetch_forecast("Nashik", "Maharashtra", test_db)

    assert result is None
