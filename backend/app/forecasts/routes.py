"""
Price Forecast routes for ML-powered price predictions.

This module provides endpoints for:
- Creating and managing forecasts (admin only)
- Querying forecasts by commodity, mandi, date range
- Getting latest forecasts for decision making
"""
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User, Commodity
from app.forecasts.schemas import (
    PriceForecastCreate, PriceForecastUpdate,
    PriceForecastResponse, PriceForecastListResponse,
)
from app.forecasts.service import PriceForecastService
from app.auth.security import get_current_user, require_role

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get Price Forecasts",
    description="Get price forecasts for a commodity from the database. Returns real predictions only.",
)
async def get_price_forecasts(
    commodity: str = Query(default="Rice", description="Commodity name"),
    days: int = Query(default=30, ge=1, le=90, description="Number of days to forecast"),
    db: Session = Depends(get_db),
):
    """
    Get price forecasts for a commodity from the database.

    Returns only real forecast data. If no forecasts exist, returns an empty
    result with a message indicating forecasts are not yet available.
    """
    # Look up the commodity
    commodity_obj = db.query(Commodity).filter(
        Commodity.name.ilike(f"%{commodity}%")
    ).first()

    if not commodity_obj:
        return {
            "commodity": commodity,
            "current_price": None,
            "forecasts": [],
            "summary": None,
            "message": f"Commodity '{commodity}' not found in the database.",
        }

    # Query real forecasts from the database
    service = PriceForecastService(db)
    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    forecasts = service.get_by_commodity(
        commodity_id=commodity_obj.id,
        start_date=today,
        end_date=end_date,
        limit=days,
    )

    if not forecasts:
        return {
            "commodity": commodity,
            "current_price": None,
            "forecasts": [],
            "summary": None,
            "message": "No forecast data available for this commodity. Forecasts will appear once ML models generate predictions.",
        }

    # Format real forecast data for the frontend
    forecast_list = []
    for f in forecasts:
        confidence_level = f.confidence_level or 0
        if confidence_level >= 0.8:
            confidence = "HIGH"
        elif confidence_level >= 0.5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        forecast_list.append({
            "date": f.forecast_date.strftime("%Y-%m-%d"),
            "predicted_price": float(f.predicted_price),
            "confidence": confidence,
            "confidence_percent": round(confidence_level * 100, 1),
            "lower_bound": round(float(f.predicted_price) * 0.95, 2),
            "upper_bound": round(float(f.predicted_price) * 1.05, 2),
            "recommendation": "HOLD",
        })

    # Calculate summary from real data
    prices = [fp["predicted_price"] for fp in forecast_list]
    peak_price = max(prices)
    peak_idx = prices.index(peak_price)

    if prices[-1] > prices[0] * 1.02:
        trend = "INCREASING"
    elif prices[-1] < prices[0] * 0.98:
        trend = "DECREASING"
    else:
        trend = "STABLE"

    return {
        "commodity": commodity,
        "current_price": forecast_list[0]["predicted_price"],
        "forecasts": forecast_list,
        "summary": {
            "trend": trend,
            "peak_date": forecast_list[peak_idx]["date"],
            "peak_price": peak_price,
            "best_sell_window": [
                forecast_list[peak_idx]["date"],
                forecast_list[min(peak_idx + 6, len(forecast_list) - 1)]["date"],
            ],
        },
    }


@router.post(
    "/",
    response_model=PriceForecastResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Forecast (Admin)",
    description="Create a new ML-powered price forecast. Requires admin role.",
    responses={
        201: {"description": "Forecast created", "model": PriceForecastResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def create_forecast(
    forecast_data: PriceForecastCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> PriceForecastResponse:
    """
    Create a new price forecast (admin only).

    Records ML model predictions with confidence scores for future prices.
    """
    service = PriceForecastService(db)
    try:
        forecast = service.create(forecast_data)
        return forecast
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/latest",
    response_model=PriceForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Forecast",
    description="Get the most recent forecast for a commodity at a mandi. Public endpoint.",
    responses={
        200: {"description": "Forecast found", "model": PriceForecastResponse},
        404: {"description": "No forecast found"},
    }
)
async def get_latest_forecast(
    commodity_id: UUID = Query(..., description="Commodity UUID"),
    mandi_id: UUID = Query(..., description="Mandi UUID"),
    db: Session = Depends(get_db),
) -> PriceForecastResponse:
    """Get the latest forecast for a commodity at a mandi."""
    service = PriceForecastService(db)
    forecast = service.get_latest(commodity_id, mandi_id)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No forecast found for this commodity and mandi",
        )
    return forecast


@router.get(
    "/{commodity_id}",
    status_code=status.HTTP_200_OK,
    summary="Get Forecasts by Commodity or Forecast ID",
    description="Get forecasts for a commodity UUID or forecast ID. Returns only real database records. Public endpoint.",
    responses={
        200: {"description": "Forecast(s) found"},
        404: {"description": "Commodity not found"},
    }
)
async def get_forecast_by_id_or_commodity(
    commodity_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    """
    Get forecasts by commodity ID or forecast ID.

    First tries to find database records by forecast ID, then by commodity ID.
    Returns an empty list if no forecasts exist (no fake data is generated).
    """
    service = PriceForecastService(db)

    # Try as forecast ID first (database record)
    forecast = service.get_by_id(commodity_id)
    if forecast:
        return [forecast]

    # Try as commodity ID (database records)
    forecasts = service.get_by_commodity(
        commodity_id=commodity_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    if forecasts:
        return forecasts

    # Verify the commodity exists
    commodity = db.query(Commodity).filter(Commodity.id == commodity_id).first()
    if not commodity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commodity not found"
        )

    # No forecasts available - return empty list (no fake data)
    return []


@router.get(
    "/commodity/{commodity_id}",
    response_model=list[PriceForecastResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Forecasts by Commodity",
    description="Get all forecasts for a specific commodity. Public endpoint.",
    responses={200: {"description": "List of forecasts"}},
)
async def get_forecasts_by_commodity(
    commodity_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[PriceForecastResponse]:
    """Get forecasts for a specific commodity."""
    service = PriceForecastService(db)
    return service.get_by_commodity(
        commodity_id=commodity_id, start_date=start_date, end_date=end_date, limit=limit,
    )


@router.get(
    "/mandi/{mandi_id}",
    response_model=list[PriceForecastResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Forecasts by Mandi",
    description="Get all forecasts for a specific mandi. Public endpoint.",
    responses={200: {"description": "List of forecasts"}},
)
async def get_forecasts_by_mandi(
    mandi_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[PriceForecastResponse]:
    """Get forecasts for a specific mandi."""
    service = PriceForecastService(db)
    return service.get_by_mandi(
        mandi_id=mandi_id, start_date=start_date, end_date=end_date, limit=limit,
    )


@router.put(
    "/{forecast_id}",
    response_model=PriceForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Forecast (Admin)",
    description="Update an existing price forecast. Requires admin role.",
    responses={
        200: {"description": "Forecast updated", "model": PriceForecastResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Forecast not found"},
    }
)
async def update_forecast(
    forecast_id: UUID,
    forecast_data: PriceForecastUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> PriceForecastResponse:
    """Update an existing forecast (admin only)."""
    service = PriceForecastService(db)
    update_data = forecast_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )
    try:
        forecast = service.update(forecast_id, forecast_data)
        if not forecast:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast not found")
        return forecast
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{forecast_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Forecast (Admin)",
    description="Delete a price forecast. Requires admin role.",
    responses={
        204: {"description": "Forecast deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Forecast not found"},
    }
)
async def delete_forecast(
    forecast_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """Delete a forecast (admin only)."""
    service = PriceForecastService(db)
    deleted = service.delete(forecast_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forecast not found")
