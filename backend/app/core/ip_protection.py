"""
IP-based brute force protection service.

Tracks failed login attempts and blocks IPs with too many failures.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.login_attempt import LoginAttempt
from app.core.config import settings


# Configuration
MAX_FAILURES_BEFORE_BLOCK = 5  # Number of failures before blocking
BLOCK_DURATION_MINUTES = 15   # How long to block an IP
FAILURE_WINDOW_MINUTES = 30   # Time window for counting failures


class IPProtectionService:
    """Service for managing IP-based brute force protection."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """
        Check if an IP address is currently blocked.
        
        An IP is blocked if it has >= MAX_FAILURES_BEFORE_BLOCK failed attempts
        in the last FAILURE_WINDOW_MINUTES, and the most recent failure was
        within BLOCK_DURATION_MINUTES.
        
        Args:
            ip_address: The IP address to check
            
        Returns:
            True if blocked, False otherwise
        """
        window_start = datetime.now(timezone.utc) - timedelta(minutes=FAILURE_WINDOW_MINUTES)
        
        # Count recent failures
        failure_count = self.db.query(func.count(LoginAttempt.id)).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.success == False,
            LoginAttempt.created_at >= window_start,
        ).scalar()
        
        if failure_count < MAX_FAILURES_BEFORE_BLOCK:
            return False
        
        # Check if the most recent failure is within block duration
        block_start = datetime.now(timezone.utc) - timedelta(minutes=BLOCK_DURATION_MINUTES)
        recent_failure = self.db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.success == False,
            LoginAttempt.created_at >= block_start,
        ).order_by(LoginAttempt.created_at.desc()).first()
        
        return recent_failure is not None
    
    def get_block_remaining_seconds(self, ip_address: str) -> Optional[int]:
        """
        Get remaining seconds until IP block expires.
        
        Returns None if IP is not blocked.
        """
        if not self.is_ip_blocked(ip_address):
            return None
        
        # Find the most recent failure
        latest_failure = self.db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.success == False,
        ).order_by(LoginAttempt.created_at.desc()).first()
        
        if not latest_failure:
            return None
        
        block_expires = latest_failure.created_at + timedelta(minutes=BLOCK_DURATION_MINUTES)
        remaining = (block_expires - datetime.now(timezone.utc)).total_seconds()
        
        return max(0, int(remaining))
    
    def record_attempt(
        self, 
        ip_address: str, 
        success: bool, 
        phone_number: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> LoginAttempt:
        """
        Record a login attempt.
        
        Args:
            ip_address: The IP address making the attempt
            success: Whether the attempt was successful
            phone_number: Optional phone number associated with attempt
            failure_reason: Optional reason for failure (e.g., "invalid_otp")
            
        Returns:
            The created LoginAttempt record
        """
        attempt = LoginAttempt(
            ip_address=ip_address,
            phone_number=phone_number,
            success=success,
            failure_reason=failure_reason if not success else None,
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt
    
    def clear_ip_attempts(self, ip_address: str) -> int:
        """
        Clear all login attempts for an IP (called on successful login).
        
        This prevents users from being blocked after successful authentication.
        
        Returns:
            Number of records deleted
        """
        result = self.db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
        ).delete()
        self.db.commit()
        return result
    
    def get_failure_count(self, ip_address: str) -> int:
        """Get the number of recent failures for an IP."""
        window_start = datetime.now(timezone.utc) - timedelta(minutes=FAILURE_WINDOW_MINUTES)
        
        return self.db.query(func.count(LoginAttempt.id)).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.success == False,
            LoginAttempt.created_at >= window_start,
        ).scalar()


def get_client_ip(request) -> str:
    """
    Extract client IP from request, handling proxies.
    
    Checks X-Forwarded-For header for proxied requests.
    """
    # Check for proxy headers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded.split(",")[0].strip()
    
    # Check for real IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client
    return request.client.host if request.client else "unknown"
