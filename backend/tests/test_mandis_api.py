import pytest
from uuid import uuid4

from tests.utils import get_auth_headers, create_test_mandi

@pytest.fixture
def test_mandi(test_db):
    """Fixture to create a test mandi."""
    return create_test_mandi(
        test_db,
        name="TestMandi",
        district="TestDistrict",
        state="TestState"
    )

def test_create_mandi_success(client, test_admin_token):
    """Test POST /mandis/ with valid data (admin required)."""
    headers = get_auth_headers(test_admin_token)
    data = {
        "name": "NewMandi",
        "district": "NewDistrict",
        "state": "NewState",
        "market_code": "MKT-NEW-001"
    }
    response = client.post("/api/v1/mandis/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["name"] == "NewMandi"
    assert resp["district"] == "NewDistrict"
    assert resp["state"] == "NewState"
    assert resp["market_code"] == "MKT-NEW-001"
    assert "id" in resp

def test_create_mandi_unauthorized(client):
    """Test POST /mandis/ without token, should return 401."""
    data = {
        "name": "UnauthorizedMandi",
        "district": "District",
        "state": "State",
        "market_code": "MKT-UNAUTH-001"
    }
    response = client.post("/api/v1/mandis/", json=data)
    assert response.status_code == 401

def test_get_mandi_by_id(client, test_mandi):
    """Test GET /mandis/{id}."""
    response = client.get(f"/api/v1/mandis/{test_mandi.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_mandi.id)
    assert data["name"] == test_mandi.name

def test_list_mandis(client, test_mandi):
    """Test GET /mandis/ with pagination."""
    response = client.get("/api/v1/mandis/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(m["id"] == str(test_mandi.id) for m in data)

def test_filter_mandis_by_state(client, test_mandi):
    """Test GET /mandis/?state=X."""
    response = client.get(f"/api/v1/mandis/?state={test_mandi.state}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(m["state"] == test_mandi.state for m in data)

def test_filter_mandis_by_district(client, test_mandi):
    """Test GET /mandis/?district={test_mandi.district}."""
    response = client.get(f"/api/v1/mandis/?district={test_mandi.district}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(m["district"] == test_mandi.district for m in data)

def test_update_mandi(client, test_admin_token, test_mandi):
    """Test PUT /mandis/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    update_data = {
        "name": "UpdatedMandi",
        "district": "UpdatedDistrict"
    }
    response = client.put(f"/api/v1/mandis/{test_mandi.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_mandi.id)
    assert data["name"] == "UpdatedMandi"
    assert data["district"] == "UpdatedDistrict"

def test_delete_mandi(client, test_admin_token, test_mandi):
    """Test DELETE /mandis/{id} (admin required)."""
    headers = get_auth_headers(test_admin_token)
    response = client.delete(f"/api/v1/mandis/{test_mandi.id}", headers=headers)
    assert response.status_code == 204  # No Content

def test_create_mandi_forbidden(client, test_token):
    """Test POST /mandis/ with non-admin token, should return 403."""
    headers = get_auth_headers(test_token)
    data = {
        "name": "ForbiddenMandi",
        "district": "District",
        "state": "State",
        "market_code": "MKT-FORBID-001"
    }
    response = client.post("/api/v1/mandis/", json=data, headers=headers)
    assert response.status_code == 403

def test_update_mandi_forbidden(client, test_token, test_mandi):
    """Test PUT /mandis/{id} with non-admin token, should return 403."""
    headers = get_auth_headers(test_token)
    update_data = {
        "name": "ShouldNotUpdate",
        "district": "ShouldNotUpdate"
    }
    response = client.put(f"/api/v1/mandis/{test_mandi.id}", json=update_data, headers=headers)
    assert response.status_code == 403

def test_delete_mandi_forbidden(client, test_token, test_mandi):
    """Test DELETE /mandis/{id} with non-admin token, should return 403."""
    headers = get_auth_headers(test_token)
    response = client.delete(f"/api/v1/mandis/{test_mandi.id}", headers=headers)
    assert response.status_code == 403