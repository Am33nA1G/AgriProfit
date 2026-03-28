"""
Commodity schemas for API requests and responses.

This module defines Pydantic models for:
- Creating commodities (admin only)
- Updating commodities (admin only)
- Commodity responses with full details
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommodityCreate(BaseModel):
    """
    Schema for creating a new commodity.

    Commodities represent agricultural products tracked in the system,
    such as rice, wheat, tomatoes, spices, etc.
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Commodity name in English",
        json_schema_extra={"example": "Rice (Ponni)"}
    )
    name_local: str | None = Field(
        default=None,
        max_length=100,
        description="Commodity name in local language (Malayalam)",
        json_schema_extra={"example": "അരി (പൊന്നി)"}
    )
    category: str | None = Field(
        default=None,
        max_length=50,
        description="Category: Grains, Vegetables, Fruits, Spices, Cash Crops, etc.",
        json_schema_extra={"example": "Grains"}
    )
    unit: str | None = Field(
        default=None,
        max_length=20,
        description="Unit of measurement: kg, quintal, dozen, piece, etc.",
        json_schema_extra={"example": "kg"}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Rice",
                    "value": {
                        "name": "Rice (Ponni)",
                        "name_local": "അരി (പൊന്നി)",
                        "category": "Grains",
                        "unit": "kg"
                    }
                },
                {
                    "summary": "Tomato",
                    "value": {
                        "name": "Tomato",
                        "name_local": "തക്കാളി",
                        "category": "Vegetables",
                        "unit": "kg"
                    }
                },
                {
                    "summary": "Cardamom",
                    "value": {
                        "name": "Cardamom",
                        "name_local": "ഏലം",
                        "category": "Spices",
                        "unit": "kg"
                    }
                }
            ]
        }
    )


class CommodityUpdate(BaseModel):
    """
    Schema for updating an existing commodity.

    All fields are optional - only provided fields will be updated.
    At least one field must be provided for the update to proceed.
    """
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Commodity name in English"
    )
    name_local: str | None = Field(
        default=None,
        max_length=100,
        description="Commodity name in local language (Malayalam)"
    )
    category: str | None = Field(
        default=None,
        max_length=50,
        description="Category: Grains, Vegetables, Fruits, Spices, etc."
    )
    unit: str | None = Field(
        default=None,
        max_length=20,
        description="Unit of measurement"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Rice (Matta)",
                "name_local": "അരി (മട്ട)"
            }
        }
    )


class CommodityResponse(BaseModel):
    """
    Schema for commodity API responses.

    Returns complete commodity information including timestamps.
    """
    id: UUID = Field(..., description="Unique commodity identifier")
    name: str = Field(..., description="Commodity name in English")
    name_local: str | None = Field(None, description="Commodity name in local language")
    category: str | None = Field(None, description="Commodity category")
    unit: str | None = Field(None, description="Unit of measurement")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Rice (Ponni)",
                "name_local": "അരി (പൊന്നി)",
                "category": "Grains",
                "unit": "kg",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class CommodityListResponse(BaseModel):
    """Schema for paginated commodity list."""
    items: list[CommodityResponse] = Field(..., description="List of commodities")
    total: int = Field(..., description="Total count matching filters")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Maximum records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "Rice (Ponni)",
                        "name_local": "അരി (പൊന്നി)",
                        "category": "Grains",
                        "unit": "kg",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 45,
                "skip": 0,
                "limit": 100
            }
        }
    )
