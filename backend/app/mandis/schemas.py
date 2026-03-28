from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Valid Kerala districts (alphabetically sorted)
KERALA_DISTRICTS = [
    "Alappuzha",
    "Ernakulam",
    "Idukki",
    "Kannur",
    "Kasaragod",
    "Kollam",
    "Kottayam",
    "Kozhikode",
    "Malappuram",
    "Palakkad",
    "Pathanamthitta",
    "Thiruvananthapuram",
    "Thrissur",
    "Wayanad",
]


class MandiBase(BaseModel):
    """Base schema for Mandi with shared fields and validation."""

    name: str = Field(..., min_length=2, max_length=255)
    state: Literal["Kerala"] = Field(default="Kerala")
    district: str = Field(..., max_length=100)
    address: str | None = Field(default=None, max_length=500)
    market_code: str = Field(..., max_length=50)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Strip whitespace from name."""
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v

    @field_validator("district")
    @classmethod
    def normalize_and_validate_district(cls, v: str) -> str:
        """Normalize district name and validate against Kerala districts."""
        v = v.strip().title()
        if v not in KERALA_DISTRICTS:
            raise ValueError(f"District must be one of: {', '.join(KERALA_DISTRICTS)}")
        return v

    @field_validator("market_code")
    @classmethod
    def normalize_market_code(cls, v: str) -> str:
        """Normalize market code to uppercase and strip whitespace."""
        v = v.strip().upper()
        if not v:
            raise ValueError("market_code cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_lat_long_pair(self):
        """Ensure latitude and longitude are provided together."""
        if (self.latitude is None) ^ (self.longitude is None):
            raise ValueError("Both latitude and longitude must be provided together")
        return self


class MandiCreate(MandiBase):
    """Schema for creating a new Mandi."""

    is_active: bool = Field(default=True)


class MandiUpdate(BaseModel):
    """Schema for updating an existing Mandi (partial updates)."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    state: Literal["Kerala"] | None = Field(default=None)
    district: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    market_code: str | None = Field(default=None, max_length=50)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str | None) -> str | None:
        """Strip whitespace from name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("name cannot be empty")
        return v

    @field_validator("district")
    @classmethod
    def normalize_and_validate_district(cls, v: str | None) -> str | None:
        """Normalize district name and validate against Kerala districts."""
        if v is not None:
            v = v.strip().title()
            if v not in KERALA_DISTRICTS:
                raise ValueError(f"District must be one of: {', '.join(KERALA_DISTRICTS)}")
        return v

    @field_validator("market_code")
    @classmethod
    def normalize_market_code(cls, v: str | None) -> str | None:
        """Normalize market code to uppercase and strip whitespace."""
        if v is not None:
            v = v.strip().upper()
            if not v:
                raise ValueError("market_code cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_lat_long_pair(self):
        """Ensure latitude and longitude are updated together if either is provided."""
        lat_provided = self.latitude is not None
        long_provided = self.longitude is not None

        if lat_provided ^ long_provided:
            raise ValueError("Both latitude and longitude must be provided together")
        return self


class MandiResponse(BaseModel):
    """Schema for Mandi API responses."""

    id: UUID
    name: str
    state: str
    district: str
    address: str | None
    market_code: str
    latitude: float | None
    longitude: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
