"""
Tests for push token registration endpoints (FR-023).

Tests:
- Register new token (201)
- Update existing token (200)
- Deactivate token (200)
- Invalid token format (422)
- Unauthenticated (401)
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.database.session import get_db
from app.auth.security import create_access_token
from tests.conftest import TestingSessionLocal, test_engine, create_sqlite_tables, drop_sqlite_tables


VALID_TOKEN = "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
VALID_TOKEN_2 = "ExponentPushToken[yyyyyyyyyyyyyyyyyyyyyy]"


@pytest.fixture(scope="function")
def client(test_db):
    """Test client with overridden database dependency."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def farmer_user(test_db):
    """Create and return a test farmer user."""
    from sqlalchemy import text
    user_id = str(uuid4())
    test_db.execute(
        text("""
            INSERT INTO users (id, phone_number, role, name, is_profile_complete, language)
            VALUES (:id, :phone, 'farmer', 'Test Farmer', 1, 'en')
        """),
        {"id": user_id, "phone": "9876543210"},
    )
    test_db.commit()
    return {"id": user_id, "phone": "9876543210"}


@pytest.fixture
def auth_headers(farmer_user):
    """Return auth headers for farmer user."""
    token = create_access_token({"sub": str(farmer_user["id"])})
    return {"Authorization": f"Bearer {token}"}


class TestRegisterPushToken:
    def test_register_new_token_returns_201(self, client, auth_headers):
        response = client.post(
            "/api/v1/notifications/push-token",
            json={
                "expo_push_token": VALID_TOKEN,
                "device_platform": "android",
                "device_model": "Samsung Galaxy A12",
                "app_version": "1.0.0",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["expo_push_token"] == VALID_TOKEN
        assert data["device_platform"] == "android"
        assert data["is_active"] is True

    def test_update_existing_token_returns_200_or_201(self, client, auth_headers):
        # Register first time
        client.post(
            "/api/v1/notifications/push-token",
            json={"expo_push_token": VALID_TOKEN, "device_platform": "android"},
            headers=auth_headers,
        )
        # Register again (upsert)
        response = client.post(
            "/api/v1/notifications/push-token",
            json={
                "expo_push_token": VALID_TOKEN,
                "device_platform": "android",
                "app_version": "1.0.1",
            },
            headers=auth_headers,
        )
        # Returns 201 for new, or 200/201 on upsert — either is acceptable
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["is_active"] is True

    def test_invalid_token_format_returns_422(self, client, auth_headers):
        response = client.post(
            "/api/v1/notifications/push-token",
            json={
                "expo_push_token": "not-a-valid-expo-token",
                "device_platform": "android",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, client):
        response = client.post(
            "/api/v1/notifications/push-token",
            json={"expo_push_token": VALID_TOKEN, "device_platform": "android"},
        )
        assert response.status_code == 401


class TestDeactivatePushToken:
    def test_deactivate_token_returns_200(self, client, auth_headers):
        # Register first
        client.post(
            "/api/v1/notifications/push-token",
            json={"expo_push_token": VALID_TOKEN_2, "device_platform": "ios"},
            headers=auth_headers,
        )
        # Deactivate
        response = client.delete(
            "/api/v1/notifications/push-token",
            json={"expo_push_token": VALID_TOKEN_2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "deactivated" in response.json().get("message", "").lower()

    def test_deactivate_nonexistent_token_returns_404(self, client, auth_headers):
        response = client.delete(
            "/api/v1/notifications/push-token",
            json={"expo_push_token": "ExponentPushToken[nonexistent000000]"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_unauthenticated_deactivate_returns_401(self, client):
        response = client.delete(
            "/api/v1/notifications/push-token",
            json={"expo_push_token": VALID_TOKEN_2},
        )
        assert response.status_code == 401
