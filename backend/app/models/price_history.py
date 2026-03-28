import uuid as uuid_module
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    commodity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("commodities.id", ondelete="CASCADE"),
        nullable=False,
    )

    mandi_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("mandis.id", ondelete="CASCADE"),
        nullable=True,
    )

    mandi_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    price_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    modal_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    min_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    max_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
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

    commodity: Mapped["Commodity"] = relationship(
        "Commodity",
        back_populates="price_history",
        passive_deletes=True,
    )

    mandi: Mapped["Mandi"] = relationship(
        "Mandi",
        back_populates="price_history",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "modal_price >= 0",
            name="check_price_non_negative",
        ),
        Index(
            "price_history_commodity_id_mandi_name_price_date_key",
            "commodity_id",
            "mandi_name",
            "price_date",
            unique=True,
        ),
        Index(
            "idx_price_history_main",
            text("commodity_id"),
            text("mandi_name"),
            text("price_date DESC"),
        ),
        Index(
            "idx_price_history_date",
            text("price_date DESC"),
        ),
        # Index for window function queries (LAG, FIRST_VALUE, LAST_VALUE)
        # Used by get_current_prices_list and transport comparisons
        Index(
            "idx_price_history_commodity_mandi_date",
            text("commodity_id"),
            text("mandi_id"),
            text("price_date DESC"),
        ),
        # Index for batch price aggregation by commodity and date
        # Used by _get_commodity_prices_from_db
        Index(
            "idx_price_history_commodity_date",
            text("commodity_id"),
            text("price_date"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceHistory commodity={self.commodity_id} "
            f"mandi={self.mandi_name} date={self.price_date} price={self.modal_price}>"
        )


__all__ = ["PriceHistory"]
