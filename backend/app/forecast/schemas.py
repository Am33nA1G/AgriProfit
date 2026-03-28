"""Forecast Pydantic schemas — API response models for price forecasts."""
from pydantic import BaseModel
from typing import Optional


class ForecastPoint(BaseModel):
    """Single forecast data point for chart rendering."""
    date: str
    price_low: Optional[float] = None
    price_mid: Optional[float] = None
    price_high: Optional[float] = None


class ForecastResponse(BaseModel):
    """API response for GET /api/v1/forecast/{commodity}/{district}.

    Includes forecast direction, predicted price range, confidence indicator,
    and tier label showing whether this is a full ML forecast or a seasonal fallback.
    """
    commodity: str
    district: str
    horizon_days: int                     # 7 or 14
    direction: str                        # "up" / "down" / "flat"
    price_low: Optional[float] = None     # lower bound of predicted range
    price_mid: Optional[float] = None     # point estimate
    price_high: Optional[float] = None    # upper bound of predicted range
    confidence_colour: str                # "Green" / "Yellow" / "Red"
    tier_label: str                       # "full model" / "seasonal average fallback"
    last_data_date: str                   # e.g. "2025-10-30"
    forecast_points: list[ForecastPoint] = []  # full series for chart
    coverage_message: Optional[str] = None     # UI-05: shown when fallback
    r2_score: Optional[float] = None           # held-out test R² from training
    data_freshness_days: int = 0               # (today - last_data_date).days
    is_stale: bool = False                     # True when data_freshness_days > 30
    n_markets: int = 0                         # len(districts_list) from meta
    typical_error_inr: Optional[float] = None  # prophet_mape * current_price, rounded to ₹10
    mape_pct: Optional[float] = None           # MAPE % at h7 (e.g. 14.1 means ±14.1%)
    model_version: Optional[str] = None        # "v5" | "legacy" | "seasonal"
