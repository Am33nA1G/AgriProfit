import uuid as uuid_module
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, DECIMAL,
    ForeignKey, Text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    phone_number: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    state: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    district: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'en'"),
    )

    is_profile_complete: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("FALSE"),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("NOW()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("NOW()"),
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
    )

    is_banned: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("FALSE"),
    )

    ban_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    community_posts: Mapped[list["CommunityPost"]] = relationship(
        "CommunityPost",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    admin_actions: Mapped[list["AdminAction"]] = relationship(
        "AdminAction",
        back_populates="admin",
        foreign_keys="[AdminAction.admin_id]",
    )

    # Security-related relationships
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(
        "UploadedFile",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    push_tokens: Mapped[list["DevicePushToken"]] = relationship(
        "DevicePushToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "phone_number ~ '^[6-9][0-9]{9}$'",
            name="check_phone_number_format",
        ),
        CheckConstraint(
            "role IN ('farmer', 'admin')",
            name="check_user_role",
        ),
        Index(
            "idx_users_phone_active",
            "phone_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_users_district", "district"),
        Index("idx_users_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} phone={self.phone_number} role={self.role}>"

__all__ = ["User"]
