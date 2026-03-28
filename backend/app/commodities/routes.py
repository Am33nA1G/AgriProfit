"""
Commodity management routes.

This module provides endpoints for:
- Listing and searching commodities (public)
- Creating, updating, deleting commodities (admin only)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.commodities.schemas import CommodityCreate, CommodityUpdate, CommodityResponse
from app.commodities.service import CommodityService
from app.auth.security import get_current_user, require_role

router = APIRouter(prefix="/commodities", tags=["Commodities"])


@router.post(
    "/",
    response_model=CommodityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Commodity (Admin)",
    description="Create a new commodity in the catalog. Requires admin role.",
    responses={
        201: {"description": "Commodity created successfully", "model": CommodityResponse},
        400: {"description": "Validation error or duplicate name", "content": {"application/json": {"example": {"detail": "Commodity with this name already exists"}}}},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def create_commodity(
    commodity_data: CommodityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> CommodityResponse:
    """
    Create a new commodity (admin only).

    Add a new agricultural commodity to the catalog. Common categories include
    Grains, Vegetables, Fruits, Spices, and Cash Crops.

    Args:
        commodity_data: CommodityCreate with name, category, unit
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Returns:
        CommodityResponse with created commodity details

    Raises:
        HTTPException 400: Validation error or duplicate name
        HTTPException 401: Not authenticated
        HTTPException 403: Not an admin
    """
    service = CommodityService(db)
    try:
        commodity = service.create(commodity_data)
        return commodity
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
@router.get(
    "/",
    response_model=list[CommodityResponse],
    status_code=status.HTTP_200_OK,
    summary="List Commodities",
    description="List all commodities with pagination. Public endpoint.",
    responses={
        200: {"description": "List of commodities"},
    }
)
async def list_commodities(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=500, description="Max records to return"),
) -> list[CommodityResponse]:
    """
    List all commodities with pagination.

    Returns a paginated list of all commodities in the catalog.
    Use this to populate dropdown selectors or browse the catalog.

    Args:
        db: Database session (injected)
        skip: Number of records to skip (pagination offset)
        limit: Maximum records to return (1-100)

    Returns:
        List of CommodityResponse objects
    """
    service = CommodityService(db)
    commodities = service.get_all(skip=skip, limit=limit)
    return commodities


@router.get(
    "/categories",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List Commodity Categories",
    description="Get all unique commodity categories.",
)
async def list_categories(
    db: Session = Depends(get_db),
) -> list[str]:
    """Get all unique commodity categories."""
    service = CommodityService(db)
    return service.get_categories()


@router.get(
    "/with-prices",
    status_code=status.HTTP_200_OK,
    summary="List Commodities with Prices",
    description="Get all commodities with current price data and advanced filtering.",
)
async def list_commodities_with_prices(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=1000, description="Max records"),
    search: str | None = Query(default=None, description="Search term"),
    categories: str | None = Query(default=None, description="Comma-separated categories"),
    min_price: float | None = Query(default=None, description="Minimum price filter"),
    max_price: float | None = Query(default=None, description="Maximum price filter"),
    trend: str | None = Query(default=None, description="Trend filter: rising, falling, stable"),
    in_season: bool | None = Query(default=None, description="Filter to in-season commodities"),
    sort_by: str = Query(default="name", description="Sort by: name, price, change"),
    sort_order: str = Query(default="asc", description="Sort order: asc, desc"),
) -> dict:
    """Get commodities with price data and advanced filtering."""
    service = CommodityService(db)
    category_list = categories.split(",") if categories else None
    return service.get_all_with_prices(
        skip=skip,
        limit=limit,
        search=search,
        categories=category_list,
        min_price=min_price,
        max_price=max_price,
        trend=trend,
        in_season=in_season,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{commodity_id}",
    response_model=CommodityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Commodity",
    description="Retrieve a single commodity by its ID. Public endpoint.",
    responses={
        200: {"description": "Commodity found", "model": CommodityResponse},
        404: {"description": "Commodity not found", "content": {"application/json": {"example": {"detail": "Commodity not found"}}}},
    }
)
async def get_commodity(
    commodity_id: UUID,
    db: Session = Depends(get_db),
) -> CommodityResponse:
    """
    Get a single commodity by ID.

    Retrieve detailed information about a commodity including its
    name, local name, category, and unit of measurement.

    Args:
        commodity_id: UUID of the commodity
        db: Database session (injected)

    Returns:
        CommodityResponse with commodity details

    Raises:
        HTTPException 404: Commodity not found
    """
    service = CommodityService(db)
    commodity = service.get_by_id(commodity_id)
    if not commodity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commodity not found",
        )
    return commodity


@router.get(
    "/{commodity_id}/details",
    status_code=status.HTTP_200_OK,
    summary="Get Commodity Details",
    description="Get detailed commodity info including price history and top mandis.",
)
async def get_commodity_details(
    commodity_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Get detailed commodity information with price history."""
    service = CommodityService(db)
    details = service.get_details(commodity_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commodity not found",
        )
    return details


@router.post(
    "/compare",
    status_code=status.HTTP_200_OK,
    summary="Compare Commodities",
    description="Compare up to 5 commodities side by side.",
)
async def compare_commodities(
    commodity_ids: list[UUID],
    db: Session = Depends(get_db),
) -> dict:
    """Compare multiple commodities."""
    if len(commodity_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 commodities required for comparison",
        )
    if len(commodity_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 commodities can be compared at once",
        )
    service = CommodityService(db)
    return service.compare(commodity_ids)


@router.get(
    "/search/",
    response_model=list[CommodityResponse],
    status_code=status.HTTP_200_OK,
    summary="Search Commodities",
    description="Search commodities by name. Public endpoint.",
    responses={
        200: {"description": "Search results"},
    }
)
async def search_commodities(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db),
) -> list[CommodityResponse]:
    """
    Search commodities by name.

    Performs a case-insensitive partial match on commodity names
    (both English and local names).

    Args:
        q: Search query string (min 1 char)
        limit: Maximum results to return (1-50)
        db: Database session (injected)

    Returns:
        List of matching CommodityResponse objects

    Example:
        >>> response = client.get("/commodities/search/?q=rice")
        >>> # Returns all commodities with "rice" in the name
    """
    service = CommodityService(db)
    commodities = service.search(query=q, limit=limit)
    return commodities


@router.put(
    "/{commodity_id}",
    response_model=CommodityResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Commodity (Admin)",
    description="Update an existing commodity. Requires admin role.",
    responses={
        200: {"description": "Commodity updated", "model": CommodityResponse},
        400: {"description": "Validation error or no fields provided"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Commodity not found"},
    }
)
async def update_commodity(
    commodity_id: UUID,
    commodity_data: CommodityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> CommodityResponse:
    """
    Update an existing commodity (admin only).

    Partially update a commodity. Only provided fields will be changed.
    At least one field must be provided.

    Args:
        commodity_id: UUID of the commodity to update
        commodity_data: CommodityUpdate with fields to change
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Returns:
        CommodityResponse with updated commodity

    Raises:
        HTTPException 400: No fields provided or validation error
        HTTPException 401: Not authenticated
        HTTPException 403: Not an admin
        HTTPException 404: Commodity not found
    """
    service = CommodityService(db)

    update_data = commodity_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )

    try:
        commodity = service.update(commodity_id, commodity_data)
        if not commodity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commodity not found",
            )
        return commodity
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{commodity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Commodity (Admin)",
    description="Delete a commodity from the catalog. Requires admin role.",
    responses={
        204: {"description": "Commodity deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Commodity not found"},
    }
)
async def delete_commodity(
    commodity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """
    Delete a commodity (admin only).

    Permanently removes a commodity from the catalog.
    Note: This may fail if there are associated price records.

    Args:
        commodity_id: UUID of the commodity to delete
        db: Database session (injected)
        current_user: Admin user (from JWT token)

    Raises:
        HTTPException 401: Not authenticated
        HTTPException 403: Not an admin
        HTTPException 404: Commodity not found
    """
    service = CommodityService(db)
    deleted = service.delete(commodity_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commodity not found",
        )
