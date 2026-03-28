"""
User schemas for API requests and responses.

This module defines Pydantic models for:
- User profile responses
- User profile updates
- Kerala district validation
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field


# Valid Kerala district codes
KERALA_DISTRICTS = [
    "KL-TVM",  # Thiruvananthapuram
    "KL-KLM",  # Kollam
    "KL-PTA",  # Pathanamthitta
    "KL-ALP",  # Alappuzha
    "KL-KTM",  # Kottayam
    "KL-IDK",  # Idukki
    "KL-EKM",  # Ernakulam
    "KL-TSR",  # Thrissur
    "KL-PKD",  # Palakkad
    "KL-MLP",  # Malappuram
    "KL-KKD",  # Kozhikode
    "KL-WYD",  # Wayanad
    "KL-KNR",  # Kannur
    "KL-KSD",  # Kasaragod
]

# District code to name mapping
DISTRICT_NAMES = {
    "KL-TVM": "Thiruvananthapuram",
    "KL-KLM": "Kollam",
    "KL-PTA": "Pathanamthitta",
    "KL-ALP": "Alappuzha",
    "KL-KTM": "Kottayam",
    "KL-IDK": "Idukki",
    "KL-EKM": "Ernakulam",
    "KL-TSR": "Thrissur",
    "KL-PKD": "Palakkad",
    "KL-MLP": "Malappuram",
    "KL-KKD": "Kozhikode",
    "KL-WYD": "Wayanad",
    "KL-KNR": "Kannur",
    "KL-KSD": "Kasaragod",
}


def get_district_name(district_value: str | None) -> str | None:
    """Get district name from district code or return the value if it's already a name."""
    if district_value is None:
        return None
    # First check if it's a district code (e.g., "KL-EKM")
    if district_value in DISTRICT_NAMES:
        return DISTRICT_NAMES[district_value]
    # If it's already a valid district name, return it as-is
    if district_value in DISTRICT_NAMES.values():
        return district_value
    # Unknown district
    return district_value


class UserResponse(BaseModel):
    """
    Schema for user profile API responses.

    Returns user details including computed district name from district code.
    """
    id: UUID = Field(..., description="Unique user identifier")
    phone_number: str = Field(..., description="10-digit Indian mobile number")
    name: str | None = Field(None, description="User's full name")
    role: str = Field(..., description="User role: 'farmer' or 'admin'")
    state: str | None = Field(None, description="State name")
    district: str | None = Field(None, description="Kerala district code (e.g., 'KL-EKM')")
    language: str = Field(..., description="Preferred language: 'en' (English) or 'ml' (Malayalam)")
    created_at: datetime = Field(..., description="Account creation timestamp")

    @computed_field
    @property
    def district_name(self) -> str | None:
        """Computed district name from district code."""
        return get_district_name(self.district)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "phone_number": "9876543210",
                "name": "Rajesh Kumar",
                "role": "farmer",
                "state": "Kerala",
                "district": "KL-EKM",
                "language": "ml",
                "created_at": "2024-01-15T10:30:00Z",
                "district_name": "Ernakulam"
            }
        }
    )


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.

    Users can update their name, state, district, and language.
    All fields are optional - only provided fields will be updated.
    """
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User's full name",
        json_schema_extra={"example": "Rajesh Kumar"}
    )
    state: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="State name",
        json_schema_extra={"example": "Kerala"}
    )
    district: str | None = Field(
        default=None,
        description="Kerala district code (e.g., 'KL-EKM' for Ernakulam)",
        json_schema_extra={"example": "KL-EKM"}
    )
    language: str | None = Field(
        default=None,
        description="Preferred language: 'en' (English) or 'ml' (Malayalam)",
        json_schema_extra={"example": "ml"}
    )

    @field_validator("district")
    @classmethod
    def validate_district(cls, v: str | None) -> str | None:
        if v is not None:
            if v not in KERALA_DISTRICTS:
                raise ValueError(f"Invalid district code. Must be one of: {', '.join(KERALA_DISTRICTS)}")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None:
            if v not in ("en", "ml"):
                raise ValueError("Language must be 'en' or 'ml'")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Update district only",
                    "value": {"district": "KL-TSR"}
                },
                {
                    "summary": "Update language only",
                    "value": {"language": "ml"}
                },
                {
                    "summary": "Update both fields",
                    "value": {"district": "KL-KKD", "language": "en"}
                }
            ]
        }
    )


class PhoneNumberUpdate(BaseModel):
    """Schema for updating phone number (requires OTP verification)."""
    new_phone_number: str = Field(
        ...,
        description="New 10-digit Indian mobile number",
        pattern=r"^[6-9]\d{9}$",
        json_schema_extra={"example": "9876543210"}
    )
    otp: str = Field(
        ...,
        description="6-digit OTP sent to new phone number",
        pattern=r"^\d{6}$",
        json_schema_extra={"example": "123456"}
    )
    request_id: str = Field(
        ...,
        description="OTP request ID from /auth/request-otp",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"}
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_phone_number": "9876543210",
                "otp": "123456",
                "request_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class UserListResponse(BaseModel):
    """Schema for paginated user list (admin only)."""
    items: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users matching filters")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "phone_number": "9876543210",
                        "role": "farmer",
                        "district": "KL-EKM",
                        "language": "ml",
                        "created_at": "2024-01-15T10:30:00Z",
                        "district_name": "Ernakulam"
                    }
                ],
                "total": 150,
                "skip": 0,
                "limit": 100
            }
        }
    )
