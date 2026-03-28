"""Forecast cache — stores pre-computed forecasts for fast cache-hit serving."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ForecastCache(Base):
    __tablename__ = "forecast_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    district_name: Mapped[str] = mapped_column(String(200), nullable=False)
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    price_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    price_mid: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    price_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    confidence_colour: Mapped[str] = mapped_column(String(10), nullable=False)
    tier_label: Mapped[str] = mapped_column(String(30), nullable=False)
    forecast_points_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_forecast_cache_lookup",
            "commodity_name",
            "district_name",
            "generated_date",
            unique=True,
        ),
    )
