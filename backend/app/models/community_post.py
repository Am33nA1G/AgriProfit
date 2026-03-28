import uuid as uuid_module
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CommunityPost(Base):
    __tablename__ = "community_posts"

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

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    post_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    district: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_admin_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="community_posts",
        passive_deletes=True,
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="post",
        passive_deletes=True,
    )

    replies: Mapped[list["CommunityReply"]] = relationship(
        "CommunityReply",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    likes: Mapped[list["CommunityLike"]] = relationship(
        "CommunityLike",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "post_type IN ('discussion', 'question', 'tip', 'announcement', 'alert')",
            name="community_posts_post_type_check",
        ),
        Index(
            "idx_posts_district_created",
            text("district"),
            text("created_at DESC"),
        ),
        Index(
            "idx_posts_type_created",
            text("post_type"),
            text("created_at DESC"),
        ),
        Index(
            "idx_posts_user_created",
            text("user_id"),
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_posts_active",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<CommunityPost id={self.id} type={self.post_type}>"

    @property
    def likes_count(self) -> int:
        return len(self.likes)

    @property
    def replies_count(self) -> int:
        return len(self.replies)


class CommunityReply(Base):
    __tablename__ = "community_replies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    post: Mapped["CommunityPost"] = relationship(
        "CommunityPost",
        back_populates="replies",
    )
    
    user: Mapped["User"] = relationship(
        "User",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<CommunityReply id={self.id} post={self.post_id}>"


class CommunityLike(Base):
    __tablename__ = "community_likes"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    post: Mapped["CommunityPost"] = relationship(
        "CommunityPost",
        back_populates="likes",
    )
    
    user: Mapped["User"] = relationship(
        "User",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<CommunityLike user={self.user_id} post={self.post_id}>"


__all__ = ["CommunityPost", "CommunityReply", "CommunityLike"]
