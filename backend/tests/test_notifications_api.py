import pytest
from uuid import uuid4
from datetime import datetime

from tests.utils import get_auth_headers
from app.models import Notification, User

@pytest.fixture
def test_notification(test_db, test_user):
    """Fixture to create a test notification for test_user."""
    notification = Notification(
        id=uuid4(),
        user_id=test_user.id,
        title="Test Notification",
        message="This is a test notification.",
        notification_type="system",
        is_read=False,
        read_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(notification)
    test_db.commit()
    test_db.refresh(notification)
    return notification

def test_create_notification(client, test_admin_token, test_user):
    """Test POST /notifications/ with valid data (admin only)."""
    headers = get_auth_headers(test_admin_token)
    data = {
        "user_id": str(test_user.id),
        "title": "New Notification",
        "message": "Notification message",
        "notification_type": "system"
    }
    response = client.post("/api/v1/notifications/", json=data, headers=headers)
    assert response.status_code == 201
    resp = response.json()
    assert resp["title"] == data["title"]
    assert resp["message"] == data["message"]
    assert resp["user_id"] == str(test_user.id)
    assert resp["notification_type"] == "system"
    assert "id" in resp

def test_get_user_notifications(client, test_token, test_user, test_notification):
    """Test GET /notifications/ returns only current user's notifications."""
    headers = get_auth_headers(test_token)
    response = client.get("/api/v1/notifications/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(n["id"] == str(test_notification.id) for n in data["items"])
    assert all(n["user_id"] == str(test_user.id) for n in data["items"])

def test_filter_notifications_by_read_status(client, test_token, test_notification):
    """Test GET /notifications/?is_read=false."""
    headers = get_auth_headers(test_token)
    response = client.get("/api/v1/notifications/?is_read=false", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(n["id"] == str(test_notification.id) for n in data["items"])
    assert all(n["is_read"] is False for n in data["items"])

def test_get_notification_by_id(client, test_token, test_notification, test_user):
    """Test GET /notifications/{id}."""
    headers = get_auth_headers(test_token)
    response = client.get(f"/api/v1/notifications/{test_notification.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_notification.id)
    assert data["user_id"] == str(test_user.id)

def test_get_other_user_notification_forbidden(client, test_token, test_db):
    """Test accessing another user's notification returns 403."""
    # Create another user and notification
    other_user = User(
        id=uuid4(),
        phone_number="9999999999",
        role="farmer",
        district="KL-KLM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)
    notification = Notification(
        id=uuid4(),
        user_id=other_user.id,
        title="Other Notification",
        message="Should not be accessible",
        notification_type="system",
        is_read=False,
        read_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(notification)
    test_db.commit()
    test_db.refresh(notification)
    headers = get_auth_headers(test_token)
    response = client.get(f"/api/v1/notifications/{notification.id}", headers=headers)
    assert response.status_code == 403

def test_mark_notification_as_read(client, test_token, test_notification, test_user):
    """Test PUT /notifications/{id}/read."""
    headers = get_auth_headers(test_token)
    response = client.put(f"/api/v1/notifications/{test_notification.id}/read", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_notification.id)
    assert data["is_read"] is True

def test_mark_all_notifications_as_read(client, test_token, test_user, test_notification):
    """Test PUT /notifications/read-all."""
    headers = get_auth_headers(test_token)
    response = client.put("/api/v1/notifications/read-all", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert isinstance(data["count"], int)
    # Optionally, verify all notifications are now read
    response2 = client.get("/api/v1/notifications/?is_read=true", headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert all(n["is_read"] is True for n in data2["items"])

def test_delete_notification(client, test_token, test_notification, test_user):
    """Test DELETE /notifications/{id}."""
    headers = get_auth_headers(test_token)
    response = client.delete(f"/api/v1/notifications/{test_notification.id}", headers=headers)
    assert response.status_code == 204  # No Content