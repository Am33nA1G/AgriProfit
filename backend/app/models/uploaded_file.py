"""
UploadedFile model for tracking file ownership.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base


class UploadedFile(Base):
    """Tracks uploaded files and their owners."""
    
    __tablename__ = "uploaded_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False, unique=True, index=True)
    original_filename = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=True)
    file_size = Column(String(50), nullable=True)  # Store as string like "2.5 MB"
    
    # Owner tracking
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    
    __table_args__ = (
        Index("ix_uploaded_files_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<UploadedFile {self.filename}>"
