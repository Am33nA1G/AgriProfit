"""
Community Post schemas for user-generated content.

This module defines Pydantic models for:
- Creating community posts (authenticated users)
- Updating posts (author or admin)
- Post responses with author information
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Post types
VALID_POST_TYPES = ["discussion", "question", "tip", "announcement", "alert"]


def _validate_title(v: str) -> str:
    """Shared title validation."""
    v = v.strip()
    if not v:
        raise ValueError("Title cannot be empty")
    if len(v) < 3:
        raise ValueError("Title must be at least 3 characters")
    return v


def _validate_content(v: str) -> str:
    """Shared content validation for posts."""
    v = v.strip()
    if not v:
        raise ValueError("Content cannot be empty")
    if len(v) < 10:
        raise ValueError("Content must be at least 10 characters")
    return v


def _validate_reply_content(v: str) -> str:
    """Content validation for replies (shorter minimum)."""
    v = v.strip()
    if not v:
        raise ValueError("Reply content cannot be empty")
    if len(v) < 1:
        raise ValueError("Reply must be at least 1 character")
    return v


def _validate_post_type(v: str) -> str:
    """Shared post type validation."""
    v = v.strip().lower()
    if v not in VALID_POST_TYPES:
        raise ValueError(f"Post type must be one of: {', '.join(VALID_POST_TYPES)}")
    return v


class CommunityPostBase(BaseModel):
    """Base schema for CommunityPost with shared fields."""

    title: str = Field(..., min_length=3, max_length=255, description="Post title")
    content: str = Field(..., min_length=10, max_length=10000, description="Post content")
    user_id: UUID
    post_type: str = Field(default="discussion", description="Type of post")
    district: str | None = Field(default=None, max_length=100, description="Related district")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _validate_title(v)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        return _validate_content(v)

    @field_validator("post_type")
    @classmethod
    def validate_post_type(cls, v: str) -> str:
        return _validate_post_type(v)


class CommunityPostCreate(BaseModel):
    """Schema for creating a new community post (user_id from auth)."""

    title: str = Field(..., min_length=3, max_length=255, description="Post title")
    content: str = Field(..., min_length=10, max_length=10000, description="Post content")
    post_type: str = Field(default="discussion", description="Type of post")
    district: str | None = Field(default=None, max_length=100, description="Related district")
    image_url: str | None = Field(default=None, max_length=500, description="Optional image URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Best practices for tomato cultivation in Kerala",
                "content": "I've been growing tomatoes in Ernakulam district for 5 years. Here are my tips for maximizing yield during monsoon season...",
                "post_type": "tip",
                "district": "KL-EKM"
            }
        }
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _validate_title(v)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        return _validate_content(v)

    @field_validator("post_type")
    @classmethod
    def validate_post_type(cls, v: str) -> str:
        return _validate_post_type(v)


class CommunityPostUpdate(BaseModel):
    """Schema for updating an existing community post."""

    title: str | None = Field(default=None, min_length=3, max_length=255)
    content: str | None = Field(default=None, min_length=10, max_length=10000)
    post_type: str | None = Field(default=None)
    district: str | None = Field(default=None, max_length=100)
    is_admin_override: bool | None = Field(default=None)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_title(v)
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_content(v)
        return v

    @field_validator("post_type")
    @classmethod
    def validate_post_type(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_post_type(v)
        return v


class CommunityReplyCreate(BaseModel):
    """Schema for creating a reply."""
    content: str = Field(..., min_length=1, max_length=1000, description="Reply content")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        return _validate_reply_content(v)


class CommunityReplyResponse(BaseModel):
    """Schema for reply response."""
    id: UUID
    post_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    
    # Optional author details if joined
    author_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CommunityPostResponse(BaseModel):
    """Schema for CommunityPost API responses."""

    id: UUID = Field(..., description="Unique post identifier")
    title: str = Field(..., description="Post title")
    content: str = Field(..., description="Post content")
    user_id: UUID = Field(..., description="Author's user ID")
    post_type: str = Field(..., description="Type of post")
    district: str | None = Field(None, description="Related district code")
    is_admin_override: bool = Field(..., description="Admin override flag")
    image_url: str | None = Field(None, description="Optional image URL")
    view_count: int = Field(default=0, description="Number of views")
    is_pinned: bool = Field(default=False, description="Whether post is pinned")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Interaction stats
    likes_count: int = Field(default=0, description="Number of upvotes")
    replies_count: int = Field(default=0, description="Number of replies")

    # User context (populated manually in service/route if needed)
    user_has_liked: bool = Field(default=False, description="If current user liked this post")

    # Author name
    author_name: str | None = Field(None, description="Author's name")

    # Alert context (populated for alert posts)
    alert_highlight: bool = Field(default=False, description="Whether to highlight this alert for the current user")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440010",
                "title": "Best practices for tomato cultivation in Kerala",
                "content": "I've been growing tomatoes in Ernakulam district for 5 years...",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "post_type": "tip",
                "district": "KL-EKM",
                "is_admin_override": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "likes_count": 5,
                "replies_count": 2,
                "user_has_liked": True
            }
        }
    )


class CommunityPostListResponse(BaseModel):
    """Schema for paginated post list."""

    items: list[CommunityPostResponse] = Field(..., description="List of posts")
    total: int = Field(..., description="Total matching posts")
    skip: int = Field(..., description="Records skipped")
    limit: int = Field(..., description="Max records returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440010",
                        "title": "Best practices for tomato cultivation",
                        "content": "Here are my tips...",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "post_type": "tip",
                        "district": "KL-EKM",
                        "is_admin_override": False,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "likes_count": 12,
                        "replies_count": 3
                    }
                ],
                "total": 50,
                "skip": 0,
                "limit": 100
            }
        }
    )


class CommunityPostWithAuthor(CommunityPostResponse):
    """Schema for post with author details."""

    author_name: str | None = None
    author_phone: str | None = None


class AlertStatusResponse(BaseModel):
    """Response for checking alert status of a post for a user."""
    is_alert: bool = Field(..., description="Whether post is an alert type")
    should_highlight: bool = Field(..., description="Whether to highlight for this user")
    in_affected_area: bool = Field(..., description="Whether user is in the affected area")
    author_district: str | None = Field(None, description="District where alert was posted")