"""
Price History schemas for API requests and responses.

This module defines Pydantic models for:
- Creating price records (admin only)
- Updating price records (admin only)
- Price history responses with validation
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PriceHistoryBase(BaseModel):
    """Base schema for PriceHistory with shared fields and validation."""

    commodity_id: UUID = Field(..., description="ID of the commodity")
    mandi_id: UUID = Field(..., description="ID of the mandi (market)")
    price_date: date = Field(..., description="Date of the price record", json_schema_extra={"example": "2024-01-15"})
    min_price: float | None = Field(default=None, gt=0, description="Minimum price per unit (Rs.)")
    max_price: float | None = Field(default=None, gt=0, description="Maximum price per unit (Rs.)")
    modal_price: float = Field(..., gt=0, description="Most common/modal price per unit (Rs.)")

    @field_validator("min_price", "max_price", "modal_price")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        """Ensure price is positive and reasonable."""
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be greater than 0")
            if v > 1000000:
                raise ValueError("Price seems unreasonably high")
            return round(v, 2)
        return v

    @model_validator(mode="after")
    def validate_price_order(self):
        """Ensure min_price <= modal_price <= max_price."""
        if self.min_price and self.max_price:
            if self.min_price > self.max_price:
                raise ValueError("min_price cannot be greater than max_price")
        if self.min_price and self.modal_price < self.min_price:
            raise ValueError("modal_price cannot be less than min_price")
        if self.max_price and self.modal_price > self.max_price:
            raise ValueError("modal_price cannot be greater than max_price")
        return self


class PriceHistoryCreate(PriceHistoryBase):
    """
    Schema for creating a new price history record.

    Records daily prices for commodities at specific mandis.
    Price validation ensures min <= modal <= max.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "price_date": "2024-01-15",
                "min_price": 42.00,
                "max_price": 48.00,
                "modal_price": 45.00
            }
        }
    )


class PriceHistoryUpdate(BaseModel):
    """Schema for updating an existing price history record."""

    price_date: date | None = Field(default=None)
    min_price: float | None = Field(default=None, gt=0)
    max_price: float | None = Field(default=None, gt=0)
    modal_price: float | None = Field(default=None, gt=0)

    @field_validator("min_price", "max_price", "modal_price")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be greater than 0")
            if v > 1000000:
                raise ValueError("Price seems unreasonably high")
            return round(v, 2)
        return v

    @model_validator(mode="after")
    def validate_price_order(self):
        if self.min_price and self.max_price:
            if self.min_price > self.max_price:
                raise ValueError("min_price cannot be greater than max_price")
        if self.modal_price:
            if self.min_price and self.modal_price < self.min_price:
                raise ValueError("modal_price cannot be less than min_price")
            if self.max_price and self.modal_price > self.max_price:
                raise ValueError("modal_price cannot be greater than max_price")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "modal_price": 46.50
            }
        }
    )


class PriceHistoryResponse(BaseModel):
    """Schema for PriceHistory API responses."""

    id: UUID = Field(..., description="Unique price record identifier")
    commodity_id: UUID = Field(..., description="Commodity ID")
    mandi_id: UUID = Field(..., description="Mandi ID")
    price_date: date = Field(..., description="Date of the price record")
    min_price: float | None = Field(None, description="Minimum price (Rs.)")
    max_price: float | None = Field(None, description="Maximum price (Rs.)")
    modal_price: float = Field(..., description="Modal price (Rs.)")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "price_date": "2024-01-15",
                "min_price": 42.00,
                "max_price": 48.00,
                "modal_price": 45.00,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class PriceHistoryListResponse(BaseModel):
    """Schema for paginated price history list."""

    items: list[PriceHistoryResponse] = Field(..., description="List of price records")
    total: int = Field(..., description="Total matching records")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Max records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440003",
                        "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                        "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                        "price_date": "2024-01-15",
                        "min_price": 42.00,
                        "max_price": 48.00,
                        "modal_price": 45.00
                    }
                ],
                "total": 500,
                "skip": 0,
                "limit": 100
            }
        }
    )


class PriceTrendResponse(BaseModel):
    """Schema for price trend data."""

    commodity_id: UUID
    mandi_id: UUID
    dates: list[date]
    min_prices: list[float]
    max_prices: list[float]
    modal_prices: list[float]
    avg_modal_price: float
    price_change_percent: float | None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "dates": ["2024-01-10", "2024-01-11", "2024-01-12"],
                "min_prices": [40.0, 41.0, 42.0],
                "max_prices": [46.0, 47.0, 48.0],
                "modal_prices": [43.0, 44.0, 45.0],
                "avg_modal_price": 44.0,
                "price_change_percent": 4.65
            }
        }
    )


class CurrentPriceResponse(BaseModel):
    """Schema for current market price list item."""

    id: UUID
    commodity_id: UUID
    commodity: str
    mandi_name: str
    state: str
    district: str
    price_per_kg: float
    change_percent: float = 0.0
    change_amount: float = 0.0
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
