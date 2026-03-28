"""
Admin Action schemas for audit logging.

This module defines Pydantic models for:
- Creating admin action logs
- Admin action responses with metadata
- Filtering and querying action history
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Valid admin action types
VALID_ACTION_TYPES = [
    "user_ban",
    "user_unban",
    "user_role_change",
    "post_delete",
    "post_restore",
    "post_override",
    "price_update",
    "price_delete",
    "forecast_update",
    "forecast_delete",
    "system_config",
    "bulk_notification",
]


def _validate_action_type(v: str) -> str:
    """Shared action type validation."""
    v = v.strip().lower()
    if v not in VALID_ACTION_TYPES:
        raise ValueError(f"Action type must be one of: {', '.join(VALID_ACTION_TYPES)}")
    return v


def _validate_description(v: str) -> str:
    """Shared description validation."""
    v = v.strip()
    if not v:
        raise ValueError("Description cannot be empty")
    if len(v) < 5:
        raise ValueError("Description must be at least 5 characters")
    return v


class AdminActionBase(BaseModel):
    """Base schema for AdminAction with shared fields."""

    admin_id: UUID
    action_type: str = Field(..., description="Type of admin action")
    target_user_id: UUID | None = Field(default=None, description="Target user ID (if applicable)")
    target_resource_id: UUID | None = Field(default=None, description="Target resource ID (if applicable)")
    description: str = Field(..., min_length=5, max_length=1000, description="Action description")
    action_metadata: dict[str, Any] | None = Field(default=None, description="Additional action action_metadata")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        return _validate_action_type(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return _validate_description(v)


class AdminActionCreate(BaseModel):
    """Schema for creating a new admin action (admin_id from auth)."""

    action_type: str = Field(..., description="Type of admin action")
    target_user_id: UUID | None = Field(default=None, description="Target user ID (if applicable)")
    target_resource_id: UUID | None = Field(default=None, description="Target resource ID (if applicable)")
    description: str = Field(..., min_length=5, max_length=1000, description="Action description")
    action_metadata: dict[str, Any] | None = Field(default=None, description="Additional action metadata")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        return _validate_action_type(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return _validate_description(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_type": "user_ban",
                "target_user_id": "550e8400-e29b-41d4-a716-446655440000",
                "description": "User banned for violating community guidelines - spam posts",
                "action_metadata": {
                    "reason": "spam",
                    "violation_count": 3
                }
            }
        }
    )


class AdminActionResponse(BaseModel):
    """Schema for AdminAction API responses."""

    id: UUID = Field(..., description="Unique action identifier")
    admin_id: UUID = Field(..., description="Admin who performed the action")
    action_type: str = Field(..., description="Type of action performed")
    target_user_id: UUID | None = Field(None, description="Affected user ID")
    target_resource_id: UUID | None = Field(None, description="Affected resource ID")
    description: str = Field(..., description="Action description")
    action_metadata: dict[str, Any] | None = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="When action was performed")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440030",
                "admin_id": "550e8400-e29b-41d4-a716-446655440005",
                "action_type": "user_ban",
                "target_user_id": "550e8400-e29b-41d4-a716-446655440000",
                "target_resource_id": None,
                "description": "User banned for spam posts",
                "action_metadata": {"reason": "spam", "violation_count": 3},
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class AdminActionListResponse(BaseModel):
    """Schema for paginated admin action list."""

    items: list[AdminActionResponse] = Field(..., description="List of admin actions")
    total: int = Field(..., description="Total matching actions")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Max records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440030",
                        "admin_id": "550e8400-e29b-41d4-a716-446655440005",
                        "action_type": "user_ban",
                        "target_user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "description": "User banned for spam",
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 100,
                "skip": 0,
                "limit": 100
            }
        }
    )


class AdminActionFilter(BaseModel):
    """Schema for filtering admin actions."""

    admin_id: UUID | None = None
    action_type: str | None = None
    target_user_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None