"""Model training log — records walk-forward validation results for each trained model."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ModelTrainingLog(Base):
    __tablename__ = "model_training_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity: Mapped[str] = mapped_column(String(200), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    n_series: Mapped[int] = mapped_column(Integer, nullable=False)
    n_folds: Mapped[int] = mapped_column(Integer, nullable=False)
    rmse_fold_1: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    rmse_fold_2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    rmse_fold_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    rmse_fold_4: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    rmse_mean: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    mape_mean: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    skforecast_version: Mapped[str] = mapped_column(String(20), nullable=False)
    xgboost_version: Mapped[str] = mapped_column(String(20), nullable=False)
    excluded_districts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_model_training_log_commodity", "commodity"),
    )
