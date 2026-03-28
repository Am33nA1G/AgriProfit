"""
Analytics schemas for market insights and statistics.

This module defines Pydantic models for:
- Price trends and statistics
- Market summaries and comparisons
- User activity tracking
- Dashboard data aggregation
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Typed sub-models for better type safety
class WeeklyPriceTrend(BaseModel):
    """Daily average price for weekly trends chart."""
    
    day: str = Field(..., description="Day abbreviation (S, M, T, W, T, F, S)")
    date: str = Field(..., description="Full date (YYYY-MM-DD)")
    value: float = Field(..., description="Average price for that day")
    
    model_config = ConfigDict(from_attributes=True)


class MandiPriceItem(BaseModel):
    """Price data for a specific mandi."""

    mandi_id: UUID = Field(..., description="Mandi identifier")
    mandi_name: str = Field(..., description="Mandi name")
    current_price: float = Field(..., description="Current modal price")
    avg_price: float = Field(..., description="Average price over period")

    model_config = ConfigDict(from_attributes=True)


class TopCommodityItem(BaseModel):
    """Top commodity by record count."""

    commodity_id: UUID = Field(..., description="Commodity identifier")
    name: str = Field(..., description="Commodity name")
    record_count: int = Field(..., description="Number of price records")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Tomato",
                "record_count": 150
            }
        }
    )


class TopMandiItem(BaseModel):
    """Top mandi by record count."""

    mandi_id: UUID = Field(..., description="Mandi identifier")
    name: str = Field(..., description="Mandi name")
    record_count: int = Field(..., description="Number of price records")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "Ernakulam Market",
                "record_count": 500
            }
        }
    )


class PriceTrendResponse(BaseModel):
    """Schema for price trend data points."""

    commodity_id: UUID = Field(..., description="Commodity identifier")
    commodity_name: str = Field(..., description="Commodity name")
    mandi_id: UUID = Field(..., description="Mandi identifier")
    mandi_name: str = Field(..., description="Mandi name")
    price_date: date = Field(..., description="Date of price record")
    modal_price: float = Field(..., description="Modal price (Rs.)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "commodity_name": "Tomato",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "mandi_name": "Ernakulam Market",
                "price_date": "2024-01-15",
                "modal_price": 45.00
            }
        }
    )


class PriceTrendListResponse(BaseModel):
    """Schema for list of price trends."""

    items: list[PriceTrendResponse]
    commodity_id: UUID
    mandi_id: UUID
    start_date: date
    end_date: date
    data_points: int


class PriceStatisticsResponse(BaseModel):
    """Schema for price statistics summary."""

    commodity_id: UUID
    commodity_name: str | None = None
    mandi_id: UUID | None = None
    mandi_name: str | None = None
    avg_price: float = Field(..., description="Average price")
    min_price: float = Field(..., description="Minimum price")
    max_price: float = Field(..., description="Maximum price")
    price_change_percent: float = Field(..., description="Price change percentage")
    data_points: int = Field(..., description="Number of data points")
    start_date: date | None = None
    end_date: date | None = None

    model_config = ConfigDict(from_attributes=True)


class MarketSummaryResponse(BaseModel):
    """Schema for overall market summary statistics."""

    total_commodities: int = Field(..., description="Total number of commodities")
    total_mandis: int = Field(..., description="Total number of mandis")
    total_price_records: int = Field(..., description="Total price history records")
    total_forecasts: int = Field(..., description="Total future forecast records")
    total_posts: int = Field(..., description="Total community posts")
    total_users: int = Field(..., description="Total registered users")
    last_updated: datetime = Field(..., description="Timestamp of last data update")
    data_is_stale: bool = Field(False, description="True if data is more than 24 hours old")
    hours_since_update: float = Field(0.0, description="Hours since last price update")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "total_commodities": 25,
                "total_mandis": 15,
                "total_price_records": 5000,
                "total_forecasts": 200,
                "total_posts": 150,
                "total_users": 500,
                "last_updated": "2024-01-15T10:30:00Z"
            }
        }
    )


class UserActivityResponse(BaseModel):
    """Schema for user activity summary."""

    user_id: UUID = Field(..., description="User identifier")
    username: str | None = Field(None, description="Username if set")
    phone: str | None = Field(None, description="Phone number (masked)")
    posts_count: int = Field(default=0, description="Number of posts by user")
    notifications_count: int = Field(default=0, description="Number of notifications")
    last_active: datetime | None = Field(default=None, description="Last activity timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "farmer_john",
                "phone": "98765***10",
                "posts_count": 12,
                "notifications_count": 25,
                "last_active": "2024-01-15T10:30:00Z"
            }
        }
    )


class UserActivityListResponse(BaseModel):
    """Schema for list of user activities."""

    items: list[UserActivityResponse]
    total: int
    skip: int
    limit: int


class CommodityPriceComparisonResponse(BaseModel):
    """Schema for comparing prices across mandis."""

    commodity_id: UUID = Field(..., description="Commodity identifier")
    commodity_name: str = Field(..., description="Commodity name")
    mandi_prices: list[MandiPriceItem] = Field(..., description="Prices at each mandi")
    lowest_price_mandi: str | None = Field(None, description="Mandi with lowest price")
    highest_price_mandi: str | None = Field(None, description="Mandi with highest price")
    price_spread: float = Field(..., description="Difference between max and min price")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "commodity_name": "Tomato",
                "mandi_prices": [
                    {"mandi_id": "...", "mandi_name": "Ernakulam", "current_price": 45.0, "avg_price": 43.5},
                    {"mandi_id": "...", "mandi_name": "Trivandrum", "current_price": 48.0, "avg_price": 46.0}
                ],
                "lowest_price_mandi": "Ernakulam Market",
                "highest_price_mandi": "Trivandrum Market",
                "price_spread": 3.0
            }
        }
    )


class MandiPerformanceResponse(BaseModel):
    """Schema for mandi performance metrics."""

    mandi_id: UUID
    mandi_name: str
    district: str | None
    total_commodities: int
    total_price_records: int
    avg_price_all_commodities: float | None
    most_traded_commodity: str | None
    data_freshness_days: int  # Days since last price update

    model_config = ConfigDict(from_attributes=True)


class ForecastAccuracyResponse(BaseModel):
    """Schema for forecast accuracy metrics."""

    commodity_id: UUID
    commodity_name: str | None = None
    mandi_id: UUID
    mandi_name: str | None = None
    model_version: str
    total_forecasts: int
    mean_absolute_error: float | None
    mean_percentage_error: float | None
    accuracy_rate: float | None  # Percentage within acceptable range

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    """Schema for dashboard summary data."""

    market_summary: MarketSummaryResponse = Field(..., description="Overall market statistics")
    recent_price_changes: list[PriceStatisticsResponse] = Field(..., description="Recent price movements")
    top_commodities: list[TopCommodityItem] = Field(..., description="Most active commodities")
    top_mandis: list[TopMandiItem] = Field(..., description="Most active mandis")
    weekly_trends: list[WeeklyPriceTrend] = Field(..., description="Last 7 days average prices")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "market_summary": {
                    "total_commodities": 25,
                    "total_mandis": 15,
                    "total_price_records": 5000,
                    "total_forecasts": 200,
                    "total_posts": 150,
                    "total_users": 500,
                    "last_updated": "2024-01-15T10:30:00Z"
                },
                "recent_price_changes": [],
                "top_commodities": [
                    {"commodity_id": "...", "name": "Tomato", "record_count": 150}
                ],
                "top_mandis": [
                    {"mandi_id": "...", "name": "Ernakulam Market", "record_count": 500}
                ]
            }
        }
    )