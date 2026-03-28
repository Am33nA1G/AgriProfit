import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, ANY
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import User, OTPRequest
from app.auth.security import hash_value

# Helper to insert OTP directly for verification tests
def create_otp(db, phone_number, otp, expires_in=300):
    otp = OTPRequest(
        phone_number=phone_number,
        otp_hash=hash_value(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        created_at=datetime.now(timezone.utc),
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp

@pytest.fixture
def phone_number():
    return "9876543210"

@pytest.fixture
def otp():
    # Use a non-test OTP to avoid bypass in development mode (test OTP is 123456)
    return "654321"

def test_request_otp_success(client, test_db, phone_number):
    """Test successful OTP request."""
    response = client.post("/api/v1/auth/request-otp", json={"phone_number": phone_number})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "OTP sent successfully"

def test_request_otp_invalid_phone(client):
    response = client.post("/api/v1/auth/request-otp", json={"phone_number": "invalid"})
    assert response.status_code == 422

def test_verify_otp_success(client, test_db, phone_number, otp):
    # Insert OTP directly
    create_otp(test_db, phone_number, otp)
    # User must exist for token to be generated
    user = User(
        id=uuid4(),
        phone_number=phone_number,
        role="farmer",
        district="KL-TVM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    response = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone_number, "otp": otp})
    assert response.status_code == 200, f"Response: {response.json()}"
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_verify_otp_invalid(client, test_db, phone_number, otp):
    # Insert correct OTP
    create_otp(test_db, phone_number, otp)
    # User must exist
    user = User(
        id=uuid4(),
        phone_number=phone_number,
        role="farmer",
        district="KL-TVM",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    # Try wrong OTP
    response = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone_number, "otp": "000000"})
    assert response.status_code in [400, 401]  # API may return 400 or 401 for invalid OTP

def test_verify_otp_expired(client, test_db, phone_number, otp):
    # Insert expired OTP
    create_otp(test_db, phone_number, otp, expires_in=-10)
    # User must exist
    user = User(
        id=uuid4(),
        phone_number=phone_number,
        role="farmer",
        district="KL-TVM",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    response = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone_number, "otp": otp})
    assert response.status_code in [400, 401]  # API may return 400 or 401 for expired OTP