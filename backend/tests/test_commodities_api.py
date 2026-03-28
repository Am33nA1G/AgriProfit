import pytest
from uuid import uuid4

from tests.utils import get_auth_headers, create_test_commodity

@pytest.fixture
def test_commodity(test_db):
    """Fixture to create a test commodity."""
    return create_test_commodity(test_db, name="TestCommodity", category="TestCategory", unit="kg")

def test_create_commodity_success(client, test_admin_token):
    """Test POST /commodities/ with valid data (admin required)."""
    headers = get_auth_headers(test_admin_token)
    data = {
        "name": "NewCommodity",
        "category": "Grains",
        "unit": "quintal"
    }
    response = client.post("/api/v1/commodities/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["name"] == "NewCommodity"
    assert resp["category"] == "Grains"
    assert resp["unit"] == "quintal"
    assert "id" in resp

def test_create_commodity_unauthorized(client):
    """Test POST /commodities/ without token, should return 401."""
    data = {
        "name": "UnauthorizedCommodity",
        "category": "Grains",
        "unit": "quintal"
    }
    response = client.post("/api/v1/commodities/", json=data)
    assert response.status_code == 401

def test_create_commodity_forbidden(client, test_token):
    """Test POST /commodities/ with non-admin token, should return 403."""
    headers = get_auth_headers(test_token)
    data = {
        "name": "ForbiddenCommodity",
        "category": "Grains",
        "unit": "quintal"
    }
    response = client.post("/api/v1/commodities/", json=data, headers=headers)
    assert response.status_code == 403

def test_get_commodity_by_id(client, test_commodity):
    """Test GET /commodities/{id}."""
    response = client.get(f"/api/v1/commodities/{test_commodity.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_commodity.id)
    assert data["name"] == test_commodity.name

def test_list_commodities(client, test_commodity):
    """Test GET /commodities/ with pagination."""
    response = client.get("/api/v1/commodities/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(c["id"] == str(test_commodity.id) for c in data)

def test_filter_commodities_by_category(client, test_commodity):
    """Test GET /commodities/?category=X."""
    response = client.get(f"/api/v1/commodities/?category={test_commodity.category}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(c["category"] == test_commodity.category for c in data)

def test_update_commodity(client, test_admin_token, test_commodity):
    """Test PUT /commodities/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    update_data = {
        "name": "UpdatedCommodity",
        "category": "UpdatedCategory"
    }
    response = client.put(f"/api/v1/commodities/{test_commodity.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_commodity.id)
    assert data["name"] == "UpdatedCommodity"
    assert data["category"] == "UpdatedCategory"

def test_update_commodity_forbidden(client, test_token, test_commodity):
    """Test PUT /commodities/{id} with non-admin token, should return 403."""
    headers = get_auth_headers(test_token)
    update_data = {
        "name": "ShouldNotUpdate",
        "category": "ShouldNotUpdate"
    }
    response = client.put(f"/api/v1/commodities/{test_commodity.id}", json=update_data, headers=headers)
    assert response.status_code == 403

def test_delete_commodity(client, test_admin_token, test_commodity):
    """Test DELETE /commodities/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    response = client.delete(f"/api/v1/commodities/{test_commodity.id}", headers=headers)
    assert response.status_code == 204  # No Content

def test_delete_commodity_forbidden(client, test_token, test_commodity):
    """Test DELETE /commodities/{id} with non-admin token, should return 403."""
    headers = get_auth_headers(test_token)
    response = client.delete(f"/api/v1/commodities/{test_commodity.id}", headers=headers)
    assert response.status_code == 403