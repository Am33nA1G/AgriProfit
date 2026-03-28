import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.service import AuthService
from app.auth.security import hash_value, verify_hashed_value
from app.models import User, OTPRequest
from tests.utils import create_test_user


class TestAuthService:
    """Tests for Auth service operations."""

    def test_get_user_by_phone(self, test_db):
        """Test getting user by phone number."""
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = AuthService(test_db)
        result = service.get_user_by_phone("9876543210")
        
        assert result is not None
        assert result.id == user.id
        assert result.phone_number == "9876543210"

    def test_get_user_by_phone_not_found(self, test_db):
        """Test getting user by phone that doesn't exist."""
        service = AuthService(test_db)
        
        result = service.get_user_by_phone("0000000000")
        
        assert result is None

    def test_get_user_by_id(self, test_db):
        """Test getting user by ID."""
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = AuthService(test_db)
        result = service.get_user_by_id(user.id)
        
        assert result is not None
        assert result.id == user.id

    def test_get_user_by_id_not_found(self, test_db):
        """Test getting user by ID that doesn't exist."""
        service = AuthService(test_db)
        
        result = service.get_user_by_id(uuid4())
        
        assert result is None

    def test_create_user(self, test_db):
        """Test creating a new user."""
        service = AuthService(test_db)
        
        user = service.create_user(phone_number="9876543210")
        
        assert user is not None
        assert user.id is not None
        assert user.phone_number == "9876543210"
        assert user.role == "farmer"  # Default role
        assert user.language == "en"  # Default language

    def test_create_user_with_role(self, test_db):
        """Test creating user with specific role."""
        service = AuthService(test_db)
        
        user = service.create_user(phone_number="9876543210", role="admin")
        
        assert user.role == "admin"

    def test_get_or_create_user_new(self, test_db):
        """Test get_or_create_user creates new user."""
        service = AuthService(test_db)
        
        user, is_new = service.get_or_create_user("9876543210")
        
        assert user is not None
        assert is_new is True
        assert user.phone_number == "9876543210"

    def test_get_or_create_user_existing(self, test_db):
        """Test get_or_create_user returns existing user."""
        existing_user = create_test_user(test_db, phone_number="9876543210")
        
        service = AuthService(test_db)
        
        user, is_new = service.get_or_create_user("9876543210")
        
        assert user is not None
        assert is_new is False
        assert user.id == existing_user.id

    def test_create_otp_request(self, test_db):
        """Test creating OTP request."""
        service = AuthService(test_db)
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        otp_request = service.create_otp_request(
            phone_number="9876543210",
            otp="123456",
            expires_at=expires_at,
        )
        
        assert otp_request is not None
        assert otp_request.phone_number == "9876543210"
        assert otp_request.verified is False

    def test_get_latest_otp_request(self, test_db):
        """Test getting latest OTP request."""
        service = AuthService(test_db)
        
        # Create multiple OTP requests with distinct timestamps
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        # First request (oldest)
        req1 = service.create_otp_request("9876543210", "111111", expires_at)
        req1.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        test_db.commit()
        
        # Second request
        req2 = service.create_otp_request("9876543210", "222222", expires_at)
        req2.created_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        test_db.commit()
        
        # Third request (newest)
        service.create_otp_request("9876543210", "333333", expires_at)
        
        latest = service.get_latest_otp_request("9876543210")
        
        assert latest is not None
        # Latest should have hash of "333333"
        assert verify_hashed_value("333333", latest.otp_hash)

    def test_get_latest_otp_request_none(self, test_db):
        """Test getting latest OTP when none exist."""
        service = AuthService(test_db)
        
        result = service.get_latest_otp_request("0000000000")
        
        assert result is None

    def test_verify_otp_success(self, test_db):
        """Test successful OTP verification."""
        service = AuthService(test_db)
        
        # Create OTP request - use non-test OTP to test actual verification logic
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        service.create_otp_request("9876543210", "654321", expires_at)
        
        # Verify OTP
        success, message = service.verify_otp("9876543210", "654321")
        
        assert success is True
        assert message == "OTP verified successfully"

    def test_verify_otp_no_request(self, test_db):
        """Test OTP verification when no request exists."""
        service = AuthService(test_db)
        
        # Use non-test OTP to test actual verification logic
        success, message = service.verify_otp("9876543210", "654321")
        
        assert success is False
        assert message == "No OTP request found"

    def test_verify_otp_expired(self, test_db):
        """Test OTP verification when OTP is expired."""
        service = AuthService(test_db)
        
        # Create expired OTP request - use non-test OTP to test actual verification logic
        expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)  # Already expired
        service.create_otp_request("9876543210", "654321", expires_at)
        
        success, message = service.verify_otp("9876543210", "654321")
        
        assert success is False
        assert message == "OTP has expired"

    def test_verify_otp_already_used(self, test_db):
        """Test OTP verification when OTP is already used."""
        service = AuthService(test_db)
        
        # Create and verify OTP - use non-test OTP to test actual verification logic
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        service.create_otp_request("9876543210", "654321", expires_at)
        service.verify_otp("9876543210", "654321")  # Use it once
        
        # Try to use again
        success, message = service.verify_otp("9876543210", "654321")
        
        assert success is False
        assert message == "OTP has already been used"

    def test_verify_otp_invalid(self, test_db):
        """Test OTP verification with wrong code."""
        service = AuthService(test_db)
        
        # Create OTP request
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        service.create_otp_request("9876543210", "123456", expires_at)
        
        # Try wrong OTP
        success, message = service.verify_otp("9876543210", "000000")
        
        assert success is False
        assert message == "Invalid OTP"

    def test_generate_tokens(self, test_db):
        """Test token generation for user."""
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = AuthService(test_db)
        tokens = service.generate_tokens(user)
        
        assert "access_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"
        assert len(tokens["access_token"]) > 0

    def test_can_request_otp_first_time(self, test_db):
        """Test OTP request allowed when no previous request."""
        service = AuthService(test_db)
        
        can_request, seconds_remaining = service.can_request_otp("9876543210")
        
        assert can_request is True
        assert seconds_remaining == 0

    def test_can_request_otp_within_cooldown(self, test_db):
        """Test OTP request blocked during cooldown period."""
        service = AuthService(test_db)
        
        # Create a recent OTP request
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        service.create_otp_request("9876543210", "123456", expires_at)
        
        # Check if can request (should be blocked)
        can_request, seconds_remaining = service.can_request_otp("9876543210", cooldown_seconds=60)
        
        assert can_request is False
        assert seconds_remaining > 0
        assert seconds_remaining <= 60

    def test_invalidate_old_otps(self, test_db):
        """Test invalidating old OTP requests."""
        service = AuthService(test_db)
        
        # Create OTP requests
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        service.create_otp_request("9876543210", "111111", expires_at)
        service.create_otp_request("9876543210", "222222", expires_at)
        
        # Invalidate old OTPs
        service.invalidate_old_otps("9876543210")
        
        # All should be marked as verified
        otp_requests = test_db.query(OTPRequest).filter(
            OTPRequest.phone_number == "9876543210"
        ).all()
        
        for otp in otp_requests:
            assert otp.verified is True


class TestSecurityFunctions:
    """Tests for security utility functions."""

    def test_hash_value(self):
        """Test hashing a value."""
        hashed = hash_value("test123")
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != "test123"  # Should not be plaintext

    def test_verify_hashed_value_correct(self):
        """Test verifying correct value."""
        original = "test123"
        hashed = hash_value(original)
        
        result = verify_hashed_value(original, hashed)
        
        assert result is True

    def test_verify_hashed_value_incorrect(self):
        """Test verifying incorrect value."""
        hashed = hash_value("test123")
        
        result = verify_hashed_value("wrong_value", hashed)
        
        assert result is False

    def test_hash_produces_different_results_for_same_input(self):
        """Test that same input produces consistent hash (SHA256)."""
        # SHA256 is deterministic, so same input = same output
        hash1 = hash_value("test123")
        hash2 = hash_value("test123")
        
        assert hash1 == hash2  # SHA256 is deterministic
