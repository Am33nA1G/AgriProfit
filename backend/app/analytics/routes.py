"""
Analytics routes for market insights and statistics.

This module provides endpoints for:
- Dashboard and market summary (public)
- Price trends and statistics (public)
- Top commodities and mandis (public)
- User activity tracking (authenticated)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.analytics.schemas import (
    PriceTrendResponse,
    PriceTrendListResponse,
    PriceStatisticsResponse,
    MarketSummaryResponse,
    UserActivityResponse,
    UserActivityListResponse,
    TopCommodityItem,
    TopMandiItem,
    CommodityPriceComparisonResponse,
    DashboardResponse,
)
from app.analytics.service import AnalyticsService
from app.auth.security import get_current_user, require_role
from app.core.rate_limit import limiter, RATE_LIMIT_ANALYTICS

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard",
    description="Get combined dashboard data including market summary, recent price changes, and top items. Public endpoint.",
    responses={200: {"description": "Dashboard data"}},
)
async def get_dashboard(
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """Get combined dashboard data (public)."""
    service = AnalyticsService(db)
    return service.get_dashboard()


@router.get(
    "/summary",
    response_model=MarketSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Market Summary",
    description="Get overall market summary statistics including totals for commodities, mandis, prices, and users. Public endpoint.",
    responses={200: {"description": "Market summary statistics"}},
)
async def get_market_summary(
    db: Session = Depends(get_db),
) -> MarketSummaryResponse:
    """Get overall market summary statistics (public)."""
    service = AnalyticsService(db)
    return service.get_market_summary()


@router.get(
    "/price-trends",
    response_model=list[PriceTrendResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Price Trends",
    description="Get historical price trends. Requires commodity_id as query parameter. Optionally filter by mandi. Public endpoint.",
    responses={
        200: {"description": "Price trend data"},
        400: {"description": "Missing required parameters"},
        404: {"description": "No price data found"},
    }
)
async def get_price_trends_query(
    db: Session = Depends(get_db),
    commodity_id: UUID | None = Query(default=None, description="Commodity UUID (required)"),
    mandi_id: UUID | None = Query(default=None, description="Filter by mandi UUID"),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
) -> list[PriceTrendResponse]:
    """
    Get price trends with query parameters.
    
    This endpoint provides the same functionality as /trends/{commodity_id}
    but accepts commodity_id as a query parameter for easier integration.
    """
    if not commodity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="commodity_id query parameter is required"
        )
    
    service = AnalyticsService(db)
    trends = service.get_price_trends(
        commodity_id=commodity_id,
        mandi_id=mandi_id,
        days=days,
    )

    if not trends:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price data found for the specified commodity",
        )

    return trends


@router.get(
    "/top-commodities",
    response_model=list[TopCommodityItem],
    status_code=status.HTTP_200_OK,
    summary="Get Top Commodities",
    description="Get top commodities by price change percentage over a specified time period. Public endpoint.",
    responses={200: {"description": "Top commodities list"}},
)
async def get_top_commodities(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50, description="Number of commodities to return"),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
) -> list[TopCommodityItem]:
    """Get top commodities by price change percentage (public)."""
    service = AnalyticsService(db)
    return service.get_top_commodities_by_price_change(limit=limit, days=days)


@router.get(
    "/top-mandis",
    response_model=list[TopMandiItem],
    status_code=status.HTTP_200_OK,
    summary="Get Top Mandis",
    description="Get top mandis by price record count. Shows most active markets. Public endpoint.",
    responses={200: {"description": "Top mandis list"}},
)
async def get_top_mandis(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50, description="Number of mandis to return"),
) -> list[TopMandiItem]:
    """Get top mandis by record count (public)."""
    service = AnalyticsService(db)
    return service.get_top_mandis_by_records(limit=limit)


@router.get(
    "/trends/{commodity_id}",
    response_model=list[PriceTrendResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Price Trends",
    description="Get historical price trends for a commodity over time. Optionally filter by mandi. Public endpoint.",
    responses={
        200: {"description": "Price trend data"},
        404: {"description": "No price data found"},
    }
)
async def get_price_trends(
    commodity_id: UUID,
    db: Session = Depends(get_db),
    mandi_id: UUID | None = Query(default=None, description="Filter by mandi"),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
) -> list[PriceTrendResponse]:
    """Get price trends for a commodity (public)."""
    service = AnalyticsService(db)
    trends = service.get_price_trends(
        commodity_id=commodity_id,
        mandi_id=mandi_id,
        days=days,
    )

    if not trends:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price data found for the specified commodity",
        )

    return trends


@router.get(
    "/trends/{commodity_id}/detailed",
    response_model=PriceTrendListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Price Trends",
    description="Get detailed price trends with metadata for a commodity at a specific mandi. Public endpoint.",
    responses={200: {"description": "Detailed trend data with metadata"}},
)
async def get_price_trends_detailed(
    commodity_id: UUID,
    mandi_id: UUID = Query(..., description="Mandi UUID (required)"),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
) -> PriceTrendListResponse:
    """Get detailed price trends with metadata (public)."""
    service = AnalyticsService(db)
    return service.get_price_trends_list(
        commodity_id=commodity_id,
        mandi_id=mandi_id,
        days=days,
    )


@router.get(
    "/statistics/{commodity_id}",
    response_model=PriceStatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Price Statistics",
    description="Get price statistics (avg, min, max, change %) for a commodity. Public endpoint.",
    responses={
        200: {"description": "Price statistics"},
        404: {"description": "No price data found"},
    }
)
async def get_price_statistics(
    commodity_id: UUID,
    db: Session = Depends(get_db),
    mandi_id: UUID | None = Query(default=None, description="Filter by mandi"),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
) -> PriceStatisticsResponse:
    """Get price statistics for a commodity (public)."""
    service = AnalyticsService(db)
    stats = service.get_price_statistics(
        commodity_id=commodity_id,
        mandi_id=mandi_id,
        days=days,
    )

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price data found for the specified commodity",
        )

    return stats


@router.get(
    "/comparison/{commodity_id}",
    response_model=CommodityPriceComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Prices Across Mandis",
    description="Compare current prices for a commodity across all mandis. Shows lowest/highest price locations. Public endpoint.",
    responses={
        200: {"description": "Price comparison data"},
        404: {"description": "No price data found"},
    }
)
async def get_commodity_price_comparison(
    commodity_id: UUID,
    db: Session = Depends(get_db),
) -> CommodityPriceComparisonResponse:
    """Compare prices for a commodity across all mandis (public)."""
    service = AnalyticsService(db)
    comparison = service.get_commodity_price_comparison(commodity_id=commodity_id)

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price data found for the specified commodity",
        )

    return comparison


@router.get(
    "/user-activity/{user_id}",
    response_model=UserActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Activity",
    description="Get activity statistics for a specific user. Users can only view their own data unless admin.",
    responses={
        200: {"description": "User activity data"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not own data and not admin)"},
        404: {"description": "User not found"},
    }
)
async def get_user_activity(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserActivityResponse:
    """Get user activity statistics (requires auth, own data or admin)."""
    # Check if user is requesting own data or is admin
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own activity",
        )

    service = AnalyticsService(db)
    activity = service.get_user_activity(user_id=user_id)

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return activity


@router.get(
    "/user-activity",
    response_model=UserActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get My Activity",
    description="Get the current user's activity statistics including post count and notifications.",
    responses={
        200: {"description": "User activity data"},
        401: {"description": "Not authenticated"},
        404: {"description": "Activity not found"},
    }
)
async def get_my_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserActivityResponse:
    """Get current user's activity statistics (requires auth)."""
    service = AnalyticsService(db)
    activity = service.get_user_activity(user_id=current_user.id)

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User activity not found",
        )

    return activity