"""
LoginAttempt model for tracking authentication attempts and IP-based protection.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from app.database.base import Base


class LoginAttempt(Base):
    """Tracks login attempts for brute force protection."""
    
    __tablename__ = "login_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request details
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 max
    phone_number = Column(String(15), nullable=True)  # Optional, for phone-specific tracking
    
    # Attempt result
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100), nullable=True)  # "invalid_otp", "expired_otp", etc.
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    __table_args__ = (
        Index("ix_login_attempts_ip_created", "ip_address", "created_at"),
        Index("ix_login_attempts_phone_created", "phone_number", "created_at"),
    )
    
    def __repr__(self):
        return f"<LoginAttempt {self.ip_address} success={self.success}>"
