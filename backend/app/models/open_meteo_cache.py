"""OpenMeteoCache — 6-hour cache for Open-Meteo API responses."""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class OpenMeteoCache(Base):
    __tablename__ = "open_meteo_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_json: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_open_meteo_cache_district_state", "district", "state", unique=True),
    )
