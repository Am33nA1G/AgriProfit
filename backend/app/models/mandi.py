import uuid as uuid_module
from datetime import datetime, time
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Time, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Mandi(Base):
    __tablename__ = "mandis"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    district: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    market_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    # Location coordinates
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    pincode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # Contact information
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Operating hours
    opening_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    closing_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    operating_days: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(20)),
        nullable=True,
        comment="Days of operation e.g. ['Monday', 'Tuesday', ...]",
    )

    # Facilities
    has_weighbridge: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    has_storage: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    has_loading_dock: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    has_cold_storage: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Payment methods
    payment_methods: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
        comment="Accepted payment methods e.g. ['Cash', 'UPI', 'Bank Transfer']",
    )

    # Commodities accepted
    commodities_accepted: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        comment="List of commodity names accepted at this mandi",
    )

    # Rating
    rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_reviews: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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

    # Relationships
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory",
        back_populates="mandi",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_mandis_state_district", "state", "district"),
        Index("idx_mandis_active_name", "is_active", "name"),
    )

    def __repr__(self) -> str:
        return f"<Mandi id={self.id} name={self.name} market_code={self.market_code}>"
