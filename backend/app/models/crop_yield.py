"""CropYield model — historical crop yield data per district."""
from typing import Optional
from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CropYield(Base):
    __tablename__ = "crop_yields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(200), nullable=False)
    crop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    area_ha: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    production_t: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    yield_kg_ha: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, default="ICRISAT")

    __table_args__ = (
        Index("idx_crop_yields_district_crop_year", "district", "crop_name", "year", unique=True),
    )
