"""Forecast accuracy log — tracks predicted vs actual prices for accuracy monitoring.

Each row represents one forecast prediction that will be compared against
actual market prices once the target date has passed.

The check_forecast_accuracy.py script fills in actual_price and
absolute_pct_error; run it weekly or daily via cron.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ForecastAccuracyLog(Base):
    __tablename__ = "forecast_accuracy_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    district_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    actual_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    absolute_pct_error: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_forecast_accuracy_lookup",
            "commodity_name",
            "district_name",
            "target_date",
            "model_version",
        ),
    )
