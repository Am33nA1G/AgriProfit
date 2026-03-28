import uuid as uuid_module
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OTPRequest(Base):
    __tablename__ = "otp_requests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    phone_number: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    otp_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    __table_args__ = (
        CheckConstraint(
            "phone_number ~ '^[6-9][0-9]{9}$'",
            name="check_otp_phone_number_format",
        ),
        Index(
            "idx_otp_phone_created",
            text("phone_number"),
            text("created_at DESC"),
        ),
        Index(
            "idx_otp_expires_at",
            "expires_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<OTPRequest phone={self.phone_number} verified={self.verified}>"

__all__ = ["OTPRequest"]
