"""YieldModelLog — tracks yield model training runs."""
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class YieldModelLog(Base):
    __tablename__ = "yield_model_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    crop_category: Mapped[str] = mapped_column(String(50), nullable=False)
    n_samples: Mapped[int] = mapped_column(Integer, nullable=False)
    n_crops: Mapped[int] = mapped_column(Integer, nullable=False)
    cv_r2_mean: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    cv_rmse_mean: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    sklearn_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
