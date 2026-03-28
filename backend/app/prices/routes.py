"""
Price History routes for daily commodity price tracking.

This module provides endpoints for:
- Recording daily prices (admin only)
- Querying historical prices with filtering
- Getting latest prices and price trends
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.prices.schemas import (
    PriceHistoryCreate,
    PriceHistoryUpdate,
    PriceHistoryResponse,
    PriceHistoryListResponse,
)
from app.prices.service import PriceHistoryService
from app.auth.security import get_current_user, require_role

router = APIRouter(prefix="/prices", tags=["Prices"])

from app.prices.schemas import CurrentPriceResponse

@router.get(
    "/current",
    response_model=dict | list[CurrentPriceResponse], # Allow wrapping or list
    summary="Get Current Market Prices",
    description="Get latest market prices for all commodities, with optional filtering.",
)
async def get_current_prices(
    commodity: str | None = Query(None, description="Search by commodity name"),
    state: str | None = Query(None, description="Filter by state"),
    db: Session = Depends(get_db),
):
    """Get current prices list."""
    service = PriceHistoryService(db)
    prices = service.get_current_prices_list(commodity=commodity, state=state)
    return {"prices": prices}


@router.get(
    "/historical",
    response_model=dict,
    summary="Get Historical Prices",
    description="Get price trend for a commodity.",
)
async def get_historical_prices(
    commodity: str = Query(..., description="Commodity name"),
    mandi_id: str = Query("all", description="Mandi ID or 'all'"),
    days: int = Query(30, description="Number of days"),
    db: Session = Depends(get_db),
):
    """Get historical prices."""
    service = PriceHistoryService(db)
    data = service.get_historical_prices(commodity=commodity, mandi_id=mandi_id, days=days)
    return {"data": data}


@router.get(
    "/top-movers",
    response_model=dict,
    summary="Get Top Movers",
    description="Get top gaining and losing commodities.",
)
async def get_top_movers(
    limit: int = Query(5, description="Number of items to return"),
    db: Session = Depends(get_db),
):
    """Get top movers."""
    service = PriceHistoryService(db)
    data = service.get_top_movers(limit=limit)
    return data


@router.post(
    "/",
    response_model=PriceHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Price Record (Admin)",
    description="Record daily prices for a commodity at a specific mandi. Requires admin role.",
    responses={
        201: {"description": "Price record created", "model": PriceHistoryResponse},
        400: {"description": "Validation error (e.g., min > max price)"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def create_price_history(
    price_data: PriceHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> PriceHistoryResponse:
    """
    Create a new price history record (admin only).

    Records the daily min/max/modal prices for a commodity at a mandi.
    Price validation ensures: min_price <= modal_price <= max_price.

    Args:
        price_data: PriceHistoryCreate with price details
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Returns:
        PriceHistoryResponse with created record

    Raises:
        HTTPException 400: Invalid price relationships or duplicate record
    """
    service = PriceHistoryService(db)
    try:
        price = service.create(price_data)
        return price
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/latest",
    response_model=PriceHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Price",
    description="Get the most recent price for a commodity at a specific mandi. Public endpoint.",
    responses={
        200: {"description": "Latest price found", "model": PriceHistoryResponse},
        404: {"description": "No price data found for this commodity/mandi combination"},
    }
)
async def get_latest_price(
    commodity_id: UUID = Query(..., description="Commodity UUID"),
    mandi_id: UUID = Query(..., description="Mandi UUID"),
    db: Session = Depends(get_db),
) -> PriceHistoryResponse:
    """
    Get the latest price for a commodity at a mandi.

    Returns the most recent price record for the specified commodity
    and mandi combination.

    Args:
        commodity_id: UUID of the commodity
        mandi_id: UUID of the mandi
        db: Database session (injected)

    Returns:
        PriceHistoryResponse with latest price

    Raises:
        HTTPException 404: No price data found
    """
    service = PriceHistoryService(db)
    price = service.get_latest(commodity_id, mandi_id)
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price history found for this commodity and mandi",
        )
    return price


@router.get(
    "/{price_id}",
    response_model=PriceHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Price Record",
    description="Retrieve a specific price history record by ID. Public endpoint.",
    responses={
        200: {"description": "Price record found", "model": PriceHistoryResponse},
        404: {"description": "Price record not found"},
    }
)
async def get_price_history(
    price_id: UUID,
    db: Session = Depends(get_db),
) -> PriceHistoryResponse:
    """Get a price history record by ID."""
    service = PriceHistoryService(db)
    price = service.get_by_id(price_id)
    if not price:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price history not found")
    return price


@router.get(
    "/",
    response_model=PriceHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Price History",
    description="List price records with filtering by commodity, mandi, and date range. Public endpoint.",
    responses={200: {"description": "Paginated price records"}},
)
async def list_price_histories(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
    commodity_id: UUID | None = Query(default=None, description="Filter by commodity"),
    mandi_id: UUID | None = Query(default=None, description="Filter by mandi"),
    start_date: date | None = Query(default=None, description="Start date (inclusive)"),
    end_date: date | None = Query(default=None, description="End date (inclusive)"),
) -> PriceHistoryListResponse:
    """
    List price history records with optional filtering.

    Supports filtering by commodity, mandi, and date range.
    Results are paginated and ordered by date descending.

    Args:
        skip: Pagination offset
        limit: Max records to return
        commodity_id: Optional commodity filter
        mandi_id: Optional mandi filter
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        PriceHistoryListResponse with paginated results
    """
    service = PriceHistoryService(db)
    prices = service.get_all(
        skip=skip, limit=limit, commodity_id=commodity_id,
        mandi_id=mandi_id, start_date=start_date, end_date=end_date,
    )
    total = service.count(
        commodity_id=commodity_id, mandi_id=mandi_id,
        start_date=start_date, end_date=end_date,
    )
    return PriceHistoryListResponse(items=prices, total=total, skip=skip, limit=limit)


@router.get(
    "/commodity/{commodity_id}",
    response_model=list[PriceHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Prices by Commodity",
    description="Get all price records for a specific commodity across all mandis. Public endpoint.",
    responses={200: {"description": "List of price records"}},
)
async def get_prices_by_commodity(
    commodity_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None, description="Start date"),
    end_date: date | None = Query(default=None, description="End date"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[PriceHistoryResponse]:
    """Get all price records for a specific commodity."""
    service = PriceHistoryService(db)
    prices = service.get_by_commodity(
        commodity_id=commodity_id, start_date=start_date, end_date=end_date, limit=limit,
    )
    return prices


@router.get(
    "/mandi/{mandi_id}",
    response_model=list[PriceHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Prices by Mandi",
    description="Get all price records for a specific mandi across all commodities. Public endpoint.",
    responses={200: {"description": "List of price records"}},
)
async def get_prices_by_mandi(
    mandi_id: UUID,
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None, description="Start date"),
    end_date: date | None = Query(default=None, description="End date"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[PriceHistoryResponse]:
    """Get all price records for a specific mandi."""
    service = PriceHistoryService(db)
    prices = service.get_by_mandi(
        mandi_id=mandi_id, start_date=start_date, end_date=end_date, limit=limit,
    )
    return prices


@router.put(
    "/{price_id}",
    response_model=PriceHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Price Record (Admin)",
    description="Update an existing price history record. Requires admin role.",
    responses={
        200: {"description": "Price record updated", "model": PriceHistoryResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Price record not found"},
    }
)
async def update_price_history(
    price_id: UUID,
    price_data: PriceHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> PriceHistoryResponse:
    """Update an existing price history record (admin only)."""
    service = PriceHistoryService(db)
    update_data = price_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )
    try:
        price = service.update(price_id, price_data)
        if not price:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price history not found")
        return price
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Price Record (Admin)",
    description="Delete a price history record. Requires admin role.",
    responses={
        204: {"description": "Price record deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Price record not found"},
    }
)
async def delete_price_history(
    price_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """Delete a price history record (admin only)."""
    service = PriceHistoryService(db)
    deleted = service.delete(price_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price history not found")
