"""
Notification schemas for user alerts and messages.

This module defines Pydantic models for:
- Creating notifications (admin only)
- Bulk notifications to multiple users
- Notification responses with read status
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Valid notification types
VALID_NOTIFICATION_TYPES = ["price_alert", "forecast", "community", "system", "announcement"]


def _validate_title(v: str) -> str:
    """Shared title validation."""
    v = v.strip()
    if not v:
        raise ValueError("Title cannot be empty")
    if len(v) < 3:
        raise ValueError("Title must be at least 3 characters")
    return v


def _validate_message(v: str) -> str:
    """Shared message validation."""
    v = v.strip()
    if not v:
        raise ValueError("Message cannot be empty")
    return v


def _validate_notification_type(v: str) -> str:
    """Shared notification type validation."""
    v = v.strip().lower()
    if v not in VALID_NOTIFICATION_TYPES:
        raise ValueError(f"Notification type must be one of: {', '.join(VALID_NOTIFICATION_TYPES)}")
    return v


class NotificationBase(BaseModel):
    """Base schema for Notification with shared fields."""

    user_id: UUID
    title: str = Field(..., min_length=3, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    related_id: UUID | None = Field(default=None, description="Related entity ID (optional)")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _validate_title(v)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return _validate_message(v)

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: str) -> str:
        return _validate_notification_type(v)


class NotificationCreate(NotificationBase):
    """Schema for creating a new notification."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Price Alert: Tomato",
                "message": "Tomato prices in Ernakulam have increased by 15% in the last 24 hours.",
                "notification_type": "price_alert",
                "related_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class NotificationUpdate(BaseModel):
    """Schema for updating a notification (mark as read)."""

    is_read: bool = Field(..., description="Mark notification as read/unread")


class NotificationResponse(BaseModel):
    """Schema for Notification API responses."""

    id: UUID = Field(..., description="Unique notification identifier")
    user_id: UUID = Field(..., description="Recipient user ID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    related_id: UUID | None = Field(None, description="Related entity ID")
    is_read: bool = Field(..., description="Read status")
    read_at: datetime | None = Field(None, description="When notification was read")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440020",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Price Alert: Tomato",
                "message": "Tomato prices in Ernakulam have increased by 15%.",
                "notification_type": "price_alert",
                "related_id": "550e8400-e29b-41d4-a716-446655440001",
                "is_read": False,
                "read_at": None,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list."""

    items: list[NotificationResponse] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total matching notifications")
    unread_count: int = Field(..., description="Count of unread notifications")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Max records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440020",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Price Alert: Tomato",
                        "message": "Prices have increased by 15%.",
                        "notification_type": "price_alert",
                        "is_read": False,
                        "read_at": None,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 25,
                "unread_count": 5,
                "skip": 0,
                "limit": 100
            }
        }
    )


class BulkNotificationCreate(BaseModel):
    """Schema for creating notifications for multiple users."""

    user_ids: list[UUID] = Field(..., min_length=1, description="List of user IDs")
    title: str = Field(..., min_length=3, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    related_id: UUID | None = Field(default=None, description="Related entity ID")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _validate_title(v)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return _validate_message(v)

    @field_validator("notification_type")
    @classmethod
    def validate_notification_type(cls, v: str) -> str:
        return _validate_notification_type(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "550e8400-e29b-41d4-a716-446655440001",
                    "550e8400-e29b-41d4-a716-446655440002"
                ],
                "title": "System Announcement",
                "message": "The platform will undergo scheduled maintenance tonight from 2 AM to 4 AM.",
                "notification_type": "announcement"
            }
        }
    )