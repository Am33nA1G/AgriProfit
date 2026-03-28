import uuid as uuid_module
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

class AdminAction(Base):
    __tablename__ = "admin_actions"
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )
    admin_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    action_metadata: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    admin: Mapped["User"] = relationship(
        "User",
        back_populates="admin_actions",
        foreign_keys=[admin_id],
        passive_deletes=True,
    )
    __table_args__ = (
        Index(
            "idx_admin_actions_admin_created",
            text("admin_id"),
            text("created_at DESC"),
        ),
        Index(
            "idx_admin_actions_type_created",
            text("action_type"),
            text("created_at DESC"),
        ),
        Index(
            "idx_admin_actions_metadata",
            text("action_metadata"),
            postgresql_using="gin",
        ),
    )
    def __repr__(self) -> str:
        return f"<AdminAction id={self.id} type={self.action_type}>"
__all__ = ["AdminAction"]