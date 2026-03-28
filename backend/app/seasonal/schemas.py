"""
Pydantic schemas for the Seasonal Price Calendar API.

Defines request/response models for the GET /api/v1/seasonal endpoint.
"""
from pydantic import BaseModel, ConfigDict


class MonthlyStatPoint(BaseModel):
    """A single month's price statistics."""
    model_config = ConfigDict(from_attributes=True)

    month: int
    month_name: str
    median_price: float
    q1_price: float
    q3_price: float
    iqr_price: float
    record_count: int
    years_of_data: int
    month_rank: int
    is_best: bool
    is_worst: bool


class SeasonalCalendarResponse(BaseModel):
    """Full seasonal calendar response for a commodity+state combination."""
    model_config = ConfigDict(from_attributes=True)

    commodity: str
    state: str
    total_years: int
    low_confidence: bool
    months: list[MonthlyStatPoint]
