import uuid as uuid_module
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

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

    post_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    notification_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        passive_deletes=True,
    )

    post: Mapped["CommunityPost | None"] = relationship(
        "CommunityPost",
        back_populates="notifications",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "(is_read = FALSE AND read_at IS NULL) OR "
            "(is_read = TRUE AND read_at IS NOT NULL)",
            name="check_read_at_consistency",
        ),
        Index(
            "idx_notifications_user_read_created",
            text("user_id"),
            text("is_read"),
            text("created_at DESC"),
        ),
        Index(
            "idx_notifications_user_created",
            text("user_id"),
            text("created_at DESC"),
        ),
        Index(
            "idx_notifications_post_id",
            text("post_id"),
            postgresql_where=text("post_id IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} read={self.is_read}>"


__all__ = ["Notification"]
