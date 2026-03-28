"""
Price Forecast schemas for ML-powered price predictions.

This module defines Pydantic models for:
- Creating forecasts (admin only)
- Updating forecasts (admin only)
- Forecast responses with confidence scores
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PriceForecastBase(BaseModel):
    """Base schema for PriceForecast with shared validation."""

    commodity_id: UUID = Field(..., description="ID of the commodity")
    mandi_id: UUID = Field(..., description="ID of the mandi")
    forecast_date: date = Field(..., description="Date for which price is forecasted")
    predicted_price: float = Field(..., gt=0, description="Predicted price per unit (Rs.)")
    confidence_level: float = Field(..., ge=0, le=1, description="Confidence score (0.0-1.0)")
    model_version: str = Field(..., min_length=1, max_length=50, description="ML model version used")

    @field_validator("predicted_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Predicted price must be greater than 0")
        if v > 1000000:
            raise ValueError("Predicted price seems unreasonably high")
        return round(v, 2)

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return round(v, 4)

    @field_validator("model_version")
    @classmethod
    def validate_model_version(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Model version cannot be empty")
        return v


class PriceForecastCreate(PriceForecastBase):
    """
    Schema for creating a new price forecast.

    Forecasts predict future prices using ML models with confidence scores.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "forecast_date": "2024-01-22",
                "predicted_price": 47.50,
                "confidence_level": 0.85,
                "model_version": "v2.1.0"
            }
        }
    )


class PriceForecastUpdate(BaseModel):
    """Schema for updating an existing price forecast."""

    predicted_price: float | None = Field(default=None, gt=0)
    confidence_level: float | None = Field(default=None, ge=0, le=1)
    model_version: str | None = Field(default=None, max_length=50)

    @field_validator("predicted_price")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        if v is not None:
            if v <= 0:
                raise ValueError("Predicted price must be greater than 0")
            if v > 1000000:
                raise ValueError("Predicted price seems unreasonably high")
            return round(v, 2)
        return v

    @field_validator("confidence_level")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        if v is not None:
            if v < 0 or v > 1:
                raise ValueError("Confidence score must be between 0 and 1")
            return round(v, 4)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "predicted_price": 48.00,
                "confidence_level": 0.88
            }
        }
    )


class PriceForecastResponse(BaseModel):
    """Schema for PriceForecast API responses."""

    id: UUID = Field(..., description="Unique forecast identifier")
    commodity_id: UUID = Field(..., description="Commodity ID")
    mandi_id: UUID | None = Field(default=None, description="Mandi ID (optional)")
    forecast_date: date = Field(..., description="Forecast target date")
    predicted_price: float = Field(..., description="Predicted price (Rs.)")
    confidence_level: float | None = Field(default=None, description="Confidence score (0-1)")
    model_version: str | None = Field(default=None, description="ML model version")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "forecast_date": "2024-01-22",
                "predicted_price": 47.50,
                "confidence_level": 0.85,
                "model_version": "v2.1.0",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class PriceForecastListResponse(BaseModel):
    """Schema for paginated forecast list."""

    items: list[PriceForecastResponse] = Field(..., description="List of forecasts")
    total: int = Field(..., description="Total matching records")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Max records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440004",
                        "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                        "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                        "forecast_date": "2024-01-22",
                        "predicted_price": 47.50,
                        "confidence_level": 0.85,
                        "model_version": "v2.1.0"
                    }
                ],
                "total": 100,
                "skip": 0,
                "limit": 100
            }
        }
    )


class ForecastAccuracyResponse(BaseModel):
    """Schema for forecast accuracy metrics."""

    commodity_id: UUID
    mandi_id: UUID
    model_version: str
    total_forecasts: int = Field(..., description="Number of forecasts analyzed")
    mean_absolute_error: float | None = Field(None, description="MAE in Rs.")
    mean_percentage_error: float | None = Field(None, description="MAPE as percentage")
    accuracy_rate: float | None = Field(None, description="Percentage within acceptable range")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "commodity_id": "550e8400-e29b-41d4-a716-446655440001",
                "mandi_id": "550e8400-e29b-41d4-a716-446655440002",
                "model_version": "v2.1.0",
                "total_forecasts": 30,
                "mean_absolute_error": 2.35,
                "mean_percentage_error": 5.2,
                "accuracy_rate": 0.87
            }
        }
    )
