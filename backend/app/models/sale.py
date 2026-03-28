import uuid as uuid_module
from datetime import datetime, timezone, date
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


def today() -> date:
    """Return current date in UTC."""
    return datetime.now(timezone.utc).date()


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[uuid_module.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid_module.uuid4,
    )

    user_id: Mapped[uuid_module.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    commodity_id: Mapped[uuid_module.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("commodities.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    
    price_per_unit: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(precision=12, scale=2), nullable=False)
    
    buyer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, default=today)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="sales")
    commodity: Mapped["Commodity"] = relationship("Commodity")

    def __repr__(self) -> str:
        return f"<Sale user={self.user_id} commodity={self.commodity_id} amount={self.total_amount}>"
