import uuid as uuid_module
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Index, String, TIMESTAMP, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.database.base import Base


class DevicePushToken(Base):
    __tablename__ = "device_push_tokens"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    expo_push_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    device_platform: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    device_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    app_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
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

    user = relationship("User", back_populates="push_tokens")

    __table_args__ = (
        UniqueConstraint("user_id", "expo_push_token", name="uq_user_push_token"),
        CheckConstraint(
            "device_platform IN ('ios', 'android')",
            name="ck_device_platform",
        ),
        Index("idx_push_tokens_user_active", "user_id", "is_active"),
        Index("idx_push_tokens_token", "expo_push_token"),
    )

    def __repr__(self) -> str:
        return f"<DevicePushToken id={self.id} user_id={self.user_id} platform={self.device_platform}>"
