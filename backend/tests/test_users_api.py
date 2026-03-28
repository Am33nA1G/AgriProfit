from uuid import uuid4
import pytest

from tests.utils import get_auth_headers

def test_get_current_user(client, test_token, test_user):
    """Test GET /users/me with valid token."""
    headers = get_auth_headers(test_token)
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["phone_number"] == test_user.phone_number
    assert data["role"] == test_user.role

def test_get_current_user_unauthorized(client):
    """Test GET /users/me without token, should return 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

def test_update_user_profile(client, test_token, test_user):
    """Test PUT /users/me with valid data."""
    headers = get_auth_headers(test_token)
    update_data = {
        "district": "KL-EKM"
    }
    response = client.put("/api/v1/users/me", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["district"] == "KL-EKM"

def test_get_user_by_id(client, test_admin_token, test_user):
    """Test GET /users/{id} with admin token."""
    headers = get_auth_headers(test_admin_token)
    response = client.get(f"/api/v1/users/{test_user.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["phone_number"] == test_user.phone_number

def test_get_users_list(client, test_admin_token, test_user):
    """Test GET /users/ with admin token and pagination."""
    headers = get_auth_headers(test_admin_token)
    response = client.get("/api/v1/users/?skip=0&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # At least the test_user should be present
    assert any(u["id"] == str(test_user.id) for u in data)