"""
Mandi (Market) management routes.

This module provides endpoints for:
- Listing, searching, and filtering mandis (public)
- Creating, updating, deleting mandis (admin only)
- Looking up mandis by market code
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.mandi.schemas import MandiCreate, MandiUpdate, MandiResponse
from app.mandi.service import MandiService
from app.auth.security import get_current_user, require_role

router = APIRouter(prefix="/mandis", tags=["Mandis"])


@router.post(
    "/",
    response_model=MandiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Mandi (Admin)",
    description="Register a new mandi (market) in the system. Requires admin role.",
    responses={
        201: {"description": "Mandi created", "model": MandiResponse},
        400: {"description": "Validation error or duplicate market code"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def create_mandi(
    mandi_data: MandiCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> MandiResponse:
    """
    Create a new mandi (admin only).

    Register a new agricultural market with location details and unique market code.

    Args:
        mandi_data: MandiCreate with market details
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Returns:
        MandiResponse with created mandi details

    Raises:
        HTTPException 400: Validation error or duplicate market code
        HTTPException 401: Not authenticated
        HTTPException 403: Not an admin
    """
    service = MandiService(db)
    try:
        mandi = service.create(mandi_data)
        return mandi
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get(
    "/",
    response_model=list[MandiResponse],
    status_code=status.HTTP_200_OK,
    summary="List Mandis",
    description="List all mandis with optional district filtering. Public endpoint.",
    responses={200: {"description": "List of mandis"}},
)
async def list_mandis(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
    district: str | None = Query(default=None, description="Filter by district name"),
) -> list[MandiResponse]:
    """
    List mandis with optional filtering.

    Args:
        db: Database session (injected)
        skip: Pagination offset
        limit: Max records to return
        district: Optional district filter

    Returns:
        List of MandiResponse objects
    """
    service = MandiService(db)
    mandis = service.get_all(skip=skip, limit=limit, district=district)
    return mandis


@router.get(
    "/{mandi_id}/prices",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
    summary="Get Mandi Prices",
    description="Get current prices for all commodities available at a specific mandi. Public endpoint.",
    responses={
        200: {"description": "List of commodity prices at this mandi"},
        404: {"description": "Mandi not found or no price data available"},
    }
)
async def get_mandi_prices(
    mandi_id: UUID,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500, description="Max commodities to return"),
) -> list[dict]:
    """
    Get current prices for all commodities at a mandi.
    
    Returns the latest price record for each commodity traded at this mandi.
    
    Args:
        mandi_id: Mandi UUID
        db: Database session
        limit: Maximum number of prices to return
    
    Returns:
        List of commodity prices with details
    """
    from app.models import PriceHistory, Commodity
    from sqlalchemy import func
    
    # Verify mandi exists
    service = MandiService(db)
    mandi = service.get_by_id(mandi_id)
    if not mandi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mandi not found"
        )
    
    # Get latest price for each commodity at this mandi
    # Using a subquery to get the max date for each commodity
    subquery = (
        db.query(
            PriceHistory.commodity_id,
            func.max(PriceHistory.price_date).label('max_date')
        )
        .filter(PriceHistory.mandi_id == mandi_id)
        .group_by(PriceHistory.commodity_id)
        .subquery()
    )
    
    prices = (
        db.query(PriceHistory, Commodity)
        .join(Commodity, PriceHistory.commodity_id == Commodity.id)
        .join(
            subquery,
            (PriceHistory.commodity_id == subquery.c.commodity_id) &
            (PriceHistory.price_date == subquery.c.max_date)
        )
        .filter(PriceHistory.mandi_id == mandi_id)
        .limit(limit)
        .all()
    )
    
    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price data available for this mandi"
        )
    
    # Format response
    return [
        {
            "commodity_id": str(commodity.id),
            "commodity_name": commodity.name,
            "commodity_category": commodity.category,
            "price": round(float(price.modal_price), 2),
            "min_price": round(float(price.min_price), 2) if price.min_price else None,
            "max_price": round(float(price.max_price), 2) if price.max_price else None,
            "price_date": price.price_date.isoformat(),
            "unit": "quintal",
            "market": mandi.name,
        }
        for price, commodity in prices
    ]


@router.get(
    "/states",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List States",
    description="Get all states with mandis.",
)
async def list_states(
    db: Session = Depends(get_db),
) -> list[str]:
    """Get all unique states with mandis."""
    service = MandiService(db)
    return service.get_states()


@router.get(
    "/districts",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List Districts by State",
    description="Get all districts in a specific state.",
)
async def list_districts(
    state: str = Query(..., description="State name"),
    db: Session = Depends(get_db),
) -> list[str]:
    """Get all districts in a state."""
    service = MandiService(db)
    return service.get_districts_by_state(state)


@router.get(
    "/with-filters",
    status_code=status.HTTP_200_OK,
    summary="List Mandis with Advanced Filters",
    description="Get all mandis with advanced filtering, distance calculation, and prices.",
)
async def list_mandis_with_filters(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=2000, description="Max records"),
    search: str | None = Query(default=None, description="Search term"),
    states: str | None = Query(default=None, description="Comma-separated states"),
    district: str | None = Query(default=None, description="District filter"),
    commodity: str | None = Query(default=None, description="Filter by commodity accepted"),
    max_distance_km: float | None = Query(default=None, description="Max distance from user"),
    user_lat: float | None = Query(default=None, description="User latitude"),
    user_lon: float | None = Query(default=None, description="User longitude"),
    user_district: str | None = Query(default=None, description="User's district"),
    user_state: str | None = Query(default=None, description="User's state"),
    has_facility: str | None = Query(default=None, description="Facility: weighbridge, storage, loading_dock, cold_storage"),
    min_rating: float | None = Query(default=None, description="Minimum rating"),
    sort_by: str = Query(default="name", description="Sort by: name, distance, rating"),
    sort_order: str = Query(default="asc", description="Sort order: asc, desc"),
) -> dict:
    """Get mandis with advanced filtering and distance from user."""
    service = MandiService(db)
    state_list = states.split(",") if states else None
    return service.get_all_with_filters(
        skip=skip,
        limit=limit,
        search=search,
        states=state_list,
        district=district,
        commodity=commodity,
        max_distance_km=max_distance_km,
        user_lat=user_lat,
        user_lon=user_lon,
        user_district=user_district,
        user_state=user_state,
        has_facility=has_facility,
        min_rating=min_rating,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{mandi_id}",
    response_model=MandiResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Mandi",
    description="Retrieve a mandi by its ID. Public endpoint.",
    responses={
        200: {"description": "Mandi found", "model": MandiResponse},
        404: {"description": "Mandi not found"},
    }
)
async def get_mandi(
    mandi_id: UUID,
    db: Session = Depends(get_db),
) -> MandiResponse:
    """
    Get a mandi by ID.

    Args:
        mandi_id: UUID of the mandi
        db: Database session (injected)

    Returns:
        MandiResponse with mandi details

    Raises:
        HTTPException 404: Mandi not found
    """
    service = MandiService(db)
    mandi = service.get_by_id(mandi_id)
    if not mandi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandi not found")
    return mandi


@router.get(
    "/{mandi_id}/details",
    status_code=status.HTTP_200_OK,
    summary="Get Mandi Details",
    description="Get detailed mandi info including prices and facilities.",
)
async def get_mandi_details(
    mandi_id: UUID,
    user_lat: float | None = Query(default=None, description="User latitude for distance"),
    user_lon: float | None = Query(default=None, description="User longitude for distance"),
    user_district: str | None = Query(default=None, description="User's district"),
    user_state: str | None = Query(default=None, description="User's state"),
    db: Session = Depends(get_db),
) -> dict:
    """Get detailed mandi information with prices."""
    service = MandiService(db)
    
    # If user_district and user_state are provided but no coordinates, geocode them
    if user_district and user_state and not (user_lat and user_lon):
        from app.core.geocoding import geocoding_service
        coords = geocoding_service.get_district_coordinates(user_district, user_state)
        if coords:
            user_lat, user_lon = coords
    
    details = service.get_details(mandi_id, user_lat, user_lon)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mandi not found",
        )
    return details


@router.post(
    "/compare",
    status_code=status.HTTP_200_OK,
    summary="Compare Mandis",
    description="Compare up to 5 mandis side by side.",
)
async def compare_mandis(
    mandi_ids: list[UUID],
    user_lat: float | None = Query(default=None, description="User latitude"),
    user_lon: float | None = Query(default=None, description="User longitude"),
    db: Session = Depends(get_db),
) -> dict:
    """Compare multiple mandis."""
    if len(mandi_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 mandis required for comparison",
        )
    if len(mandi_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 mandis can be compared at once",
        )
    service = MandiService(db)
    return service.compare(mandi_ids, user_lat, user_lon)


@router.get(
    "/search/",
    response_model=list[MandiResponse],
    status_code=status.HTTP_200_OK,
    summary="Search Mandis",
    description="Search mandis by name or market code. Public endpoint.",
    responses={200: {"description": "Search results"}},
)
async def search_mandis(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db),
) -> list[MandiResponse]:
    """
    Search mandis by name or market code.

    Args:
        q: Search query
        limit: Max results
        db: Database session (injected)

    Returns:
        List of matching mandis
    """
    service = MandiService(db)
    mandis = service.search(query=q, limit=limit)
    return mandis


@router.get(
    "/by-code/{market_code}",
    response_model=MandiResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Mandi by Code",
    description="Retrieve a mandi by its unique market code. Public endpoint.",
    responses={
        200: {"description": "Mandi found", "model": MandiResponse},
        404: {"description": "Mandi not found"},
    }
)
async def get_mandi_by_code(
    market_code: str,
    db: Session = Depends(get_db),
) -> MandiResponse:
    """
    Get a mandi by market code.

    Args:
        market_code: Unique market identifier (e.g., 'KL-EKM-001')
        db: Database session (injected)

    Returns:
        MandiResponse with mandi details

    Raises:
        HTTPException 404: Mandi not found
    """
    service = MandiService(db)
    mandi = service.get_by_market_code(market_code)
    if not mandi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandi not found")
    return mandi


@router.put(
    "/{mandi_id}",
    response_model=MandiResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Mandi (Admin)",
    description="Update an existing mandi. Requires admin role.",
    responses={
        200: {"description": "Mandi updated", "model": MandiResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Mandi not found"},
    }
)
async def update_mandi(
    mandi_id: UUID,
    mandi_data: MandiUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> MandiResponse:
    """
    Update an existing mandi (admin only).

    Args:
        mandi_id: UUID of the mandi
        mandi_data: MandiUpdate with fields to change
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Returns:
        MandiResponse with updated details

    Raises:
        HTTPException 400: Validation error
        HTTPException 404: Mandi not found
    """
    service = MandiService(db)
    update_data = mandi_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )
    try:
        mandi = service.update(mandi_id, mandi_data)
        if not mandi:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandi not found")
        return mandi
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{mandi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Mandi (Admin)",
    description="Soft delete a mandi. Requires admin role.",
    responses={
        204: {"description": "Mandi deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Mandi not found"},
    }
)
async def delete_mandi(
    mandi_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """
    Soft delete a mandi (admin only).

    Args:
        mandi_id: UUID of the mandi to delete
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Raises:
        HTTPException 404: Mandi not found
    """
    service = MandiService(db)
    deleted = service.delete(mandi_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mandi not found")
