import pytest
from datetime import date, timedelta, datetime
from uuid import uuid4

from tests.utils import get_auth_headers, create_test_commodity, create_test_mandi
from app.models import PriceHistory

@pytest.fixture
def test_commodity(test_db):
    return create_test_commodity(test_db, name="TestCommodity", category="TestCategory", unit="kg")

@pytest.fixture
def test_mandi(test_db):
    return create_test_mandi(test_db, name="TestMandi", district="TestDistrict", state="TestState")

@pytest.fixture
def test_price(test_db, test_commodity, test_mandi):
    """Fixture to create a test price history record."""
    price = PriceHistory(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        price_date=date.today(),
        modal_price=2000,
        min_price=1800,
        max_price=2200,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(price)
    test_db.commit()
    test_db.refresh(price)
    return price

def test_create_price_history(client, test_admin_token, test_commodity, test_mandi):
    """Test POST /prices/ with valid data (admin required)."""
    headers = get_auth_headers(test_admin_token)
    data = {
        "commodity_id": str(test_commodity.id),
        "mandi_id": str(test_mandi.id),
        "price_date": str(date.today()),
        "modal_price": 2100,
        "min_price": 2000,
        "max_price": 2200
    }
    response = client.post("/api/v1/prices/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["commodity_id"] == str(test_commodity.id)
    assert resp["mandi_id"] == str(test_mandi.id)
    assert resp["modal_price"] == 2100

def test_create_price_unauthorized(client, test_commodity, test_mandi):
    """Test POST /prices/ without token, should return 401."""
    data = {
        "commodity_id": str(test_commodity.id),
        "mandi_id": str(test_mandi.id),
        "price_date": str(date.today()),
        "modal_price": 2100,
        "min_price": 2000,
        "max_price": 2200
    }
    response = client.post("/api/v1/prices/", json=data)
    assert response.status_code == 401

def test_get_price_by_id(client, test_price):
    """Test GET /prices/{id}."""
    response = client.get(f"/api/v1/prices/{test_price.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_price.id)
    assert data["modal_price"] == test_price.modal_price

def test_list_prices(client, test_price):
    """Test GET /prices/ with pagination."""
    response = client.get("/api/v1/prices/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(p["id"] == str(test_price.id) for p in data["items"])

def test_filter_prices_by_commodity(client, test_price):
    """Test GET /prices/?commodity_id=X."""
    response = client.get(f"/api/v1/prices/?commodity_id={test_price.commodity_id}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(p["commodity_id"] == str(test_price.commodity_id) for p in data["items"])

def test_filter_prices_by_date_range(client, test_db, test_commodity, test_mandi):
    """Test GET /prices/?start_date=X&end_date=Y."""
    # Create two prices on different dates
    price1 = PriceHistory(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        price_date=date.today() - timedelta(days=2),
        modal_price=1900,
        min_price=1800,
        max_price=2000,
        created_at=datetime.utcnow() - timedelta(days=2),
        updated_at=datetime.utcnow() - timedelta(days=2),
    )
    price2 = PriceHistory(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        price_date=date.today(),
        modal_price=2100,
        min_price=2000,
        max_price=2200,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(price1)
    test_db.add(price2)
    test_db.commit()
    # Query for date range that includes only price2
    start = date.today() - timedelta(days=1)
    end = date.today()
    response = client.get(f"/api/v1/prices/?start_date={start}&end_date={end}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(p["id"] == str(price2.id) for p in data["items"])
    assert all(start <= date.fromisoformat(p["price_date"]) <= end for p in data["items"])

def test_get_latest_price(client, test_db, test_commodity, test_mandi):
    """Test GET /prices/latest?commodity_id=X&mandi_id=Y."""
    # Create two prices, latest should be returned
    price1 = PriceHistory(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        price_date=date.today() - timedelta(days=1),
        modal_price=2000,
        min_price=1900,
        max_price=2100,
        created_at=datetime.utcnow() - timedelta(days=1),
        updated_at=datetime.utcnow() - timedelta(days=1),
    )
    price2 = PriceHistory(
        id=uuid4(),
        commodity_id=test_commodity.id,
        mandi_id=test_mandi.id,
        price_date=date.today(),
        modal_price=2200,
        min_price=2100,
        max_price=2300,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(price1)
    test_db.add(price2)
    test_db.commit()
    response = client.get(f"/api/v1/prices/latest?commodity_id={test_commodity.id}&mandi_id={test_mandi.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(price2.id)
    assert data["modal_price"] == 2200

def test_update_price(client, test_admin_token, test_price):
    """Test PUT /prices/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    update_data = {
        "modal_price": 2500,
        "min_price": 2400,
        "max_price": 2600
    }
    response = client.put(f"/api/v1/prices/{test_price.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_price.id)
    assert data["modal_price"] == 2500

def test_delete_price(client, test_admin_token, test_price):
    """Test DELETE /prices/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    response = client.delete(f"/api/v1/prices/{test_price.id}", headers=headers)
    assert response.status_code == 204  # No Content