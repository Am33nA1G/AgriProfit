import pytest
from uuid import uuid4
from datetime import date, datetime, timedelta

from tests.utils import get_auth_headers, create_test_commodity, create_test_mandi
from app.models import PriceForecast

@pytest.fixture
def test_commodity(test_db):
    return create_test_commodity(test_db, name="ForecastCommodity")

@pytest.fixture
def test_mandi(test_db):
    return create_test_mandi(test_db, name="ForecastMandi")

@pytest.fixture
def test_forecast(test_db, test_commodity, test_mandi):
    """Fixture to create a test price forecast record."""
    forecast = PriceForecast(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        forecast_date=date.today(),
        predicted_price=2500,
        confidence_level=0.85,
        model_version="v1.0",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(forecast)
    test_db.commit()
    test_db.refresh(forecast)
    return forecast

def test_create_forecast(client, test_admin_token, test_commodity, test_mandi):
    """Test POST /forecasts/ with valid data (admin required)."""
    headers = get_auth_headers(test_admin_token)
    data = {
        "commodity_id": str(test_commodity.id),
        "mandi_id": str(test_mandi.id),
        "forecast_date": str(date.today()),
        "predicted_price": 2600,
        "confidence_level": 0.9,
        "model_version": "v1.0"
    }
    response = client.post("/api/v1/forecasts/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["commodity_id"] == str(test_commodity.id)
    assert resp["mandi_id"] == str(test_mandi.id)
    assert resp["predicted_price"] == 2600
    assert resp["confidence_level"] == 0.9
    assert resp["model_version"] == "v1.0"

def test_create_forecast_unauthorized(client, test_commodity, test_mandi):
    """Test POST /forecasts/ without token, should return 401."""
    data = {
        "commodity_id": str(test_commodity.id),
        "mandi_id": str(test_mandi.id),
        "forecast_date": str(date.today()),
        "predicted_price": 2600,
        "confidence_level": 0.9,
        "model_version": "v1.0"
    }
    response = client.post("/api/v1/forecasts/", json=data)
    assert response.status_code == 401

def test_get_forecast_by_id(client, test_forecast):
    """Test GET /forecasts/{commodity_id} returns list of forecasts for that commodity."""
    response = client.get(f"/api/v1/forecasts/{test_forecast.commodity_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(f["id"] == str(test_forecast.id) for f in data)

def test_list_forecasts(client, test_forecast):
    """Test GET /forecasts/{commodity_id} returns list of forecasts for that commodity."""
    response = client.get(f"/api/v1/forecasts/{test_forecast.commodity_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(f["id"] == str(test_forecast.id) for f in data)

def test_filter_forecasts_by_commodity(client, test_forecast):
    """Test GET /forecasts/commodity/{commodity_id} returns list filtered by commodity."""
    response = client.get(f"/api/v1/forecasts/commodity/{test_forecast.commodity_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(f["commodity_id"] == str(test_forecast.commodity_id) for f in data)

def test_filter_forecasts_by_date_range(client, test_db, test_commodity, test_mandi):
    """Test GET /forecasts/commodity/{commodity_id}?start_date=X&end_date=Y."""
    # Create two forecasts on different dates
    forecast1 = PriceForecast(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        forecast_date=date.today() - timedelta(days=2),
        predicted_price=2400,
        confidence_level=0.8,
        model_version="v1.0",
        created_at=datetime.utcnow() - timedelta(days=2),
        updated_at=datetime.utcnow() - timedelta(days=2),
    )
    forecast2 = PriceForecast(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        forecast_date=date.today(),
        predicted_price=2600,
        confidence_level=0.9,
        model_version="v1.0",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(forecast1)
    test_db.add(forecast2)
    test_db.commit()
    # Query for date range that includes only forecast2
    start = date.today() - timedelta(days=1)
    end = date.today()
    response = client.get(
        f"/api/v1/forecasts/commodity/{test_commodity.id}?start_date={start}&end_date={end}"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(f["id"] == str(forecast2.id) for f in data)
    assert all(start <= date.fromisoformat(f["forecast_date"]) <= end for f in data)

def test_get_latest_forecast(client, test_commodity, test_mandi, test_forecast):
    """Test GET /forecasts/latest?commodity_id=X&mandi_id=Y."""
    response = client.get(f"/api/v1/forecasts/latest?commodity_id={test_commodity.id}&mandi_id={test_mandi.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["commodity_id"] == str(test_commodity.id)
    assert data["mandi_id"] == str(test_mandi.id)

def test_update_forecast(client, test_admin_token, test_forecast):
    """Test PUT /forecasts/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    update_data = {
        "predicted_price": 2700,
        "confidence_level": 0.95,
        "model_version": "v1.1"
    }
    response = client.put(f"/api/v1/forecasts/{test_forecast.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_forecast.id)
    assert data["predicted_price"] == 2700
    assert data["confidence_level"] == 0.95
    assert data["model_version"] == "v1.1"

def test_delete_forecast(client, test_admin_token, test_forecast):
    """Test DELETE /forecasts/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    response = client.delete(f"/api/v1/forecasts/{test_forecast.id}", headers=headers)
    assert response.status_code == 204  # No Content