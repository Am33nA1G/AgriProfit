"""
Forecast routes — FastAPI endpoint for price forecasts.

GET /api/v1/forecast/{commodity}/{district}

IMPORTANT: Uses `def` (not `async def`) because get_or_load_model()
calls joblib.load() which is disk I/O. FastAPI runs `def` handlers in
a threadpool automatically, avoiding event loop blocking.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.forecast.schemas import ForecastResponse
from app.forecast.service import ForecastService

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get(
    "/{commodity}/{district}",
    response_model=ForecastResponse,
    summary="Price Forecast",
    description="""
Returns a 7-day or 14-day price forecast for a commodity-district pair.

Served from forecast_cache (target <= 50ms on cache hit).
Returns tier_label='seasonal average fallback' for districts with < 365 days of price data.
Data note: price history ends 2025-10-30; forecast starts from last available price date.
""",
)
def get_forecast(
    commodity: str,
    district: str,
    horizon: int = Query(
        default=14,
        ge=7,
        le=14,
        description="Forecast horizon in days: 7 or 14",
    ),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    """Get a price forecast for a commodity-district pair."""
    service = ForecastService(db)
    return service.get_forecast(commodity, district, horizon)
