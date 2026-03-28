"""
RefreshToken model for JWT refresh token management.
"""
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class RefreshToken(Base):
    """Stores refresh tokens for JWT authentication."""
    
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Store hash of token, not the token itself
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # Owner
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Token metadata
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Device/session info (optional)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    __table_args__ = (
        Index("ix_refresh_tokens_user_expires", "user_id", "expires_at"),
        Index("ix_refresh_tokens_user_active", "user_id", "revoked"),
    )
    
    @staticmethod
    def generate_token() -> str:
        """Generate a secure random refresh token."""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @classmethod
    def create_for_user(cls, user_id: uuid.UUID, expires_days: int = 30, 
                        device_info: str = None, ip_address: str = None):
        """Create a new refresh token for a user."""
        token = cls.generate_token()
        return cls(
            user_id=user_id,
            token_hash=cls.hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            device_info=device_info,
            ip_address=ip_address,
        ), token  # Return both the model and the plaintext token
    
    def is_valid(self) -> bool:
        """Check if token is valid (not expired or revoked)."""
        if self.revoked:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
    
    def revoke(self):
        """Revoke this refresh token."""
        self.revoked = True
        self.revoked_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<RefreshToken {self.id} user={self.user_id}>"
