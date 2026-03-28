"""
Notification routes for user alerts and messages.

This module provides endpoints for:
- Creating notifications (admin only)
- Retrieving and filtering user notifications
- Managing read/unread status
- Bulk notification operations
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.notifications.schemas import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    BulkNotificationCreate,
    VALID_NOTIFICATION_TYPES,
)
from app.notifications.service import NotificationService
from app.auth.security import get_current_user, require_role
from app.core.rate_limit import limiter, RATE_LIMIT_READ, RATE_LIMIT_WRITE

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post(
    "/",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Notification (Admin)",
    description="Create a new notification for a user. Requires admin role.",
    responses={
        201: {"description": "Notification created", "model": NotificationResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def create_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> NotificationResponse:
    """Create a new notification (admin only)."""
    service = NotificationService(db)
    try:
        notification = service.create(notification_data)
        return notification
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/bulk",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Bulk Notifications (Admin)",
    description="Send the same notification to multiple users at once. Requires admin role.",
    responses={
        201: {"description": "Notifications created"},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def create_bulk_notifications(
    bulk_data: BulkNotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[NotificationResponse]:
    """Create notifications for multiple users (admin only)."""
    service = NotificationService(db)
    try:
        notifications = service.bulk_create(bulk_data)
        return notifications
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get My Notifications",
    description="Get current user's notifications with optional filtering by read status and type.",
    responses={
        200: {"description": "Paginated notifications"},
        400: {"description": "Invalid notification type"},
        401: {"description": "Not authenticated"},
    }
)
async def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
    is_read: bool | None = Query(default=None, description="Filter by read status"),
    notification_type: str | None = Query(default=None, description="Filter by type"),
) -> NotificationListResponse:
    """Get current user's notifications with optional filtering."""
    # Validate notification_type if provided
    if notification_type and notification_type not in VALID_NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification_type. Must be one of: {', '.join(VALID_NOTIFICATION_TYPES)}",
        )

    service = NotificationService(db)

    notifications = service.get_user_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_read=is_read,
        notification_type=notification_type,
    )

    total = service.count(
        user_id=current_user.id,
        is_read=is_read,
        notification_type=notification_type,
    )

    unread_count = service.count_unread(user_id=current_user.id)

    return NotificationListResponse(
        items=notifications,
        total=total,
        unread_count=unread_count,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/unread-count",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Unread Count",
    description="Get the count of unread notifications for the current user.",
    responses={
        200: {"description": "Unread count"},
        401: {"description": "Not authenticated"},
    }
)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get count of unread notifications for current user."""
    service = NotificationService(db)
    count = service.count_unread(user_id=current_user.id)
    return {"unread_count": count}


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Notification",
    description="Retrieve a specific notification by ID. Users can only access their own notifications.",
    responses={
        200: {"description": "Notification found", "model": NotificationResponse},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not owner)"},
        404: {"description": "Notification not found"},
    }
)
async def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Get a single notification by ID (owner only)."""
    service = NotificationService(db)
    notification = service.get_by_id(notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Verify ownership
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own notifications",
        )

    return notification


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark as Read",
    description="Mark a notification as read. Users can only mark their own notifications.",
    responses={
        200: {"description": "Marked as read", "model": NotificationResponse},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not owner)"},
        404: {"description": "Notification not found"},
    }
)
async def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark a notification as read (owner only)."""
    service = NotificationService(db)

    # Check if notification exists and belongs to user
    existing = service.get_by_id(notification_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only mark your own notifications as read",
        )

    notification = service.mark_as_read(notification_id, user_id=current_user.id)
    return notification


@router.put(
    "/{notification_id}/unread",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark as Unread",
    description="Mark a notification as unread. Users can only mark their own notifications.",
    responses={
        200: {"description": "Marked as unread", "model": NotificationResponse},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not owner)"},
        404: {"description": "Notification not found"},
    }
)
async def mark_notification_as_unread(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark a notification as unread (owner only)."""
    service = NotificationService(db)

    existing = service.get_by_id(notification_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only mark your own notifications as unread",
        )

    notification = service.mark_as_unread(notification_id, user_id=current_user.id)
    return notification


@router.put(
    "/read-all",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Mark All as Read",
    description="Mark all notifications as read for the current user.",
    responses={
        200: {"description": "All marked as read"},
        401: {"description": "Not authenticated"},
    }
)
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark all notifications as read for current user."""
    service = NotificationService(db)
    count = service.mark_all_as_read(user_id=current_user.id)
    return {"message": f"Marked {count} notifications as read", "count": count}


@router.delete(
    "/read",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete All Read",
    description="Delete all read notifications for the current user to clean up inbox.",
    responses={
        200: {"description": "Read notifications deleted"},
        401: {"description": "Not authenticated"},
    }
)
async def delete_all_read_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete all read notifications for current user."""
    service = NotificationService(db)
    count = service.delete_all_read(user_id=current_user.id)
    return {"message": f"Deleted {count} read notifications", "count": count}


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notification",
    description="Delete a specific notification. Users can only delete their own notifications.",
    responses={
        204: {"description": "Notification deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not owner)"},
        404: {"description": "Notification not found"},
    }
)
async def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a notification (owner only)."""
    service = NotificationService(db)

    existing = service.get_by_id(notification_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own notifications",
        )

    deleted = service.delete(notification_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )