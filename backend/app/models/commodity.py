import uuid as uuid_module
from datetime import datetime
from uuid import UUID
from sqlalchemy import String, DateTime, Text, Integer, Boolean, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Commodity(Base):
    __tablename__ = "commodities"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    name_local: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Description for detailed view
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Seasonal information
    growing_months: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
        comment="Months when crop is grown [1-12]",
    )

    harvest_months: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
        comment="Months when crop is harvested [1-12]",
    )

    peak_season_start: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Start month of peak selling season (1-12)",
    )

    peak_season_end: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="End month of peak selling season (1-12)",
    )

    # Regional information
    major_producing_states: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        comment="Top producing states for this commodity",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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

    # 🔥 REQUIRED RELATIONSHIPS 🔥
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory",
        back_populates="commodity",
        cascade="all, delete-orphan",
    )

    price_forecasts: Mapped[list["PriceForecast"]] = relationship(
        "PriceForecast",
        back_populates="commodity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_commodities_active_name", "is_active", "name"),
        Index("idx_commodities_active_category", "is_active", "category"),
    )

    def __repr__(self) -> str:
        return f"<Commodity id={self.id} name={self.name}>"
