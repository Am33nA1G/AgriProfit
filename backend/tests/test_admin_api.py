import pytest
from uuid import uuid4
from datetime import datetime

from tests.utils import get_auth_headers
from app.models import AdminAction, User

@pytest.fixture
def test_admin_action(test_db, test_user):
    """Fixture to create a test admin action for test_user."""
    admin = User(
        id=uuid4(),
        phone_number="9999999999",
        role="admin",
        district="KL-EKM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    action = AdminAction(
        id=uuid4(),
        admin_id=admin.id,
        target_user_id=test_user.id,
        action_type="user_ban",
        description="Banned for testing",
        created_at=datetime.utcnow(),
    )
    test_db.add(action)
    test_db.commit()
    test_db.refresh(action)
    return action

def test_create_admin_action(client, test_admin_token, test_user):
    """Test POST /admin/actions/ with valid data."""
    headers = get_auth_headers(test_admin_token)
    data = {
        "target_user_id": str(test_user.id),
        "action_type": "user_ban",
        "description": "Banned for testing"
    }
    response = client.post("/api/v1/admin/actions/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["target_user_id"] == str(test_user.id)
    assert resp["action_type"] == "user_ban"
    assert resp["description"] == "Banned for testing"
    assert "id" in resp

def test_create_admin_action_unauthorized(client, test_user):
    """Test POST /admin/actions/ without token, should return 401."""
    data = {
        "target_user_id": str(test_user.id),
        "action_type": "user_ban",
        "description": "Banned for testing"
    }
    response = client.post("/api/v1/admin/actions/", json=data)
    assert response.status_code == 401

def test_get_admin_action_by_id(client, test_admin_token, test_admin_action):
    """Test GET /admin/actions/{id}."""
    headers = get_auth_headers(test_admin_token)
    response = client.get(f"/api/v1/admin/actions/{test_admin_action.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_admin_action.id)
    assert data["action_type"] == test_admin_action.action_type

def test_list_admin_actions(client, test_admin_token, test_admin_action):
    """Test GET /admin/actions/ with pagination."""
    headers = get_auth_headers(test_admin_token)
    response = client.get("/api/v1/admin/actions/?skip=0&limit=10", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(a["id"] == str(test_admin_action.id) for a in data["items"])

def test_filter_admin_actions_by_type(client, test_admin_token, test_admin_action):
    """Test GET /admin/actions/?action_type=X."""
    headers = get_auth_headers(test_admin_token)
    response = client.get(f"/api/v1/admin/actions/?action_type={test_admin_action.action_type}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(a["action_type"] == test_admin_action.action_type for a in data["items"])

def test_filter_admin_actions_by_admin(client, test_admin_token, test_admin_action):
    """Test GET /admin/actions/?admin_id=X."""
    headers = get_auth_headers(test_admin_token)
    response = client.get(f"/api/v1/admin/actions/?admin_id={test_admin_action.admin_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(a["admin_id"] == str(test_admin_action.admin_id) for a in data["items"])

def test_get_user_admin_actions(client, test_admin_token, test_user, test_admin_action):
    """Test GET /admin/actions/user/{user_id}."""
    headers = get_auth_headers(test_admin_token)
    response = client.get(f"/api/v1/admin/actions/user/{test_user.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(a["target_user_id"] == str(test_user.id) for a in data)