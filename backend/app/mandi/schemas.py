"""
Mandi (Market) schemas for API requests and responses.

This module defines Pydantic models for:
- Creating mandis (admin only)
- Updating mandis (admin only)
- Mandi responses with location details
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MandiCreate(BaseModel):
    """
    Schema for creating a new mandi (agricultural market).

    Mandis are physical marketplaces where farmers sell their produce.
    Each mandi has a unique market code and geographic location.
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Mandi name",
        json_schema_extra={"example": "Ernakulam Main Market"}
    )
    state: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="State name",
        json_schema_extra={"example": "Kerala"}
    )
    district: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="District name",
        json_schema_extra={"example": "Ernakulam"}
    )
    address: str | None = Field(
        default=None,
        max_length=500,
        description="Full address",
        json_schema_extra={"example": "Market Road, Ernakulam, Kerala 682011"}
    )
    market_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unique market identifier code",
        json_schema_extra={"example": "KL-EKM-001"}
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude coordinate",
        json_schema_extra={"example": 9.9312}
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude coordinate",
        json_schema_extra={"example": 76.2673}
    )
    is_active: bool = Field(
        default=True,
        description="Whether the mandi is currently active"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ernakulam Main Market",
                "state": "Kerala",
                "district": "Ernakulam",
                "address": "Market Road, Ernakulam, Kerala 682011",
                "market_code": "KL-EKM-001",
                "latitude": 9.9312,
                "longitude": 76.2673,
                "is_active": True
            }
        }
    )


class MandiUpdate(BaseModel):
    """
    Schema for updating an existing mandi.

    All fields are optional - only provided fields will be updated.
    """
    name: str | None = Field(default=None, min_length=1, max_length=200)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    district: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    market_code: str | None = Field(default=None, min_length=1, max_length=50)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "address": "New Market Complex, Ernakulam",
                "is_active": True
            }
        }
    )


class MandiResponse(BaseModel):
    """
    Schema for mandi API responses.

    Returns complete mandi information including location coordinates.
    """
    id: UUID = Field(..., description="Unique mandi identifier")
    name: str = Field(..., description="Mandi name")
    state: str = Field(..., description="State name")
    district: str = Field(..., description="District name")
    address: str | None = Field(None, description="Full address")
    market_code: str = Field(..., description="Unique market code")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    is_active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "Ernakulam Main Market",
                "state": "Kerala",
                "district": "Ernakulam",
                "address": "Market Road, Ernakulam, Kerala 682011",
                "market_code": "KL-EKM-001",
                "latitude": 9.9312,
                "longitude": 76.2673,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class MandiListResponse(BaseModel):
    """Schema for paginated mandi list."""
    items: list[MandiResponse] = Field(..., description="List of mandis")
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Max records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "name": "Ernakulam Main Market",
                        "state": "Kerala",
                        "district": "Ernakulam",
                        "market_code": "KL-EKM-001",
                        "latitude": 9.9312,
                        "longitude": 76.2673,
                        "is_active": True
                    }
                ],
                "total": 120,
                "skip": 0,
                "limit": 100
            }
        }
    )
