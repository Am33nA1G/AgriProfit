"""
Admin Action routes for audit logging and moderation.

This module provides endpoints for:
- Logging admin actions (admin only)
- Querying action history by user, resource, type
- Getting action summaries and statistics
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.models.community_post import CommunityPost
from app.admin.schemas import (
    AdminActionCreate,
    AdminActionResponse,
    AdminActionListResponse,
    VALID_ACTION_TYPES,
)
from app.admin.service import AdminActionService
from app.auth.security import require_role
from app.core.rate_limit import limiter, RATE_LIMIT_READ, RATE_LIMIT_WRITE
from app.core.logging_config import log_admin_action

router = APIRouter(prefix="/admin", tags=["Admin"])

# Dashboard Management Endpoints
@router.get(
    "/stats",
    summary="Get Admin Dashboard Stats",
    description="Get statistics for admin dashboard",
)
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get dashboard statistics."""
    total_users = db.query(User).count()
    banned_users = db.query(User).filter(User.is_banned == True).count()
    total_posts = db.query(CommunityPost).count()
    active_users = db.query(User).filter(User.is_banned == False).count()
    
    return {
        "total_users": total_users,
        "total_posts": total_posts,
        "banned_users": banned_users,
        "active_users": active_users,
    }


@router.get(
    "/users",
    summary="Get All Users",
    description="Get list of all users with optional search",
)
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    search: str = Query(default="", description="Search by name, phone, or location"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Get all users with search."""
    query = db.query(User)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_filter)) |
            (User.phone_number.ilike(search_filter)) |
            (User.district.ilike(search_filter))
        )
    
    users = query.offset(skip).limit(limit).all()
    
    return [{
        "id": str(user.id),
        "name": user.name,
        "phone": user.phone_number,
        "location": f"{user.district}, {user.state}" if user.district and user.state else (user.district or user.state or ""),
        "role": user.role,
        "is_banned": user.is_banned,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    } for user in users]


@router.get(
    "/posts",
    summary="Get All Posts",
    description="Get list of all community posts with optional search",
)
async def get_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    search: str = Query(default="", description="Search by title or author"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Get all posts with search."""
    query = db.query(CommunityPost)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (CommunityPost.title.ilike(search_filter)) |
            (CommunityPost.content.ilike(search_filter))
        )
    
    posts = query.offset(skip).limit(limit).all()
    
    return [{
        "id": str(post.id),
        "title": post.title,
        "content": post.content,
        "category": post.post_type,  # post_type, not category
        "author_id": str(post.user_id),
        "author_name": post.user.name if post.user else "Unknown",
        "likes_count": post.likes_count,
        "comments_count": post.replies_count,  # replies_count, not comments_count
        "created_at": post.created_at.isoformat() if post.created_at else None,
    } for post in posts]


@router.put(
    "/users/{user_id}/ban",
    summary="Ban User",
    description="Ban a user from the platform",
)
async def ban_user(
    user_id: UUID,
    reason: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Ban a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_banned = True
    user.ban_reason = reason.get("reason", "No reason provided")
    db.commit()
    
    return {"message": "User banned successfully"}


@router.put(
    "/users/{user_id}/unban",
    summary="Unban User",
    description="Unban a previously banned user",
)
async def unban_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Unban a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_banned = False
    user.ban_reason = None
    db.commit()
    
    return {"message": "User unbanned successfully"}


@router.delete(
    "/posts/{post_id}",
    summary="Delete Post",
    description="Delete a community post",
)
async def delete_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Delete a post."""
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    
    return {"message": "Post deleted successfully"}


# Admin Actions Audit Log Endpoints
actions_router = APIRouter(prefix="/actions", tags=["Admin"])


@actions_router.post(
    "/",
    response_model=AdminActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log Admin Action",
    description="Create a new admin action log entry for audit purposes. Requires admin role.",
    responses={
        201: {"description": "Action logged", "model": AdminActionResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
@limiter.limit(RATE_LIMIT_WRITE)
async def create_admin_action(
    request: Request,
    response: Response,
    action_data: AdminActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> AdminActionResponse:
    """Create a new admin action log entry (admin only)."""
    # Get client IP for logging
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not client_ip and request.client:
        client_ip = request.client.host

    service = AdminActionService(db)
    try:
        action = service.create(action_data, admin_id=current_user.id)

        # Log to security log
        log_admin_action(
            admin_id=str(current_user.id),
            action_type=action_data.action_type,
            target_id=str(action_data.target_user_id or action_data.target_resource_id or ""),
            description=action_data.description,
            ip_address=client_ip or "unknown",
        )

        return action
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@actions_router.get(
    "/summary",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get Action Summary",
    description="Get summary count of actions grouped by type. Useful for dashboards. Requires admin role.",
    responses={
        200: {"description": "Action summary by type"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def get_action_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    start_date: datetime | None = Query(default=None, description="Filter from date"),
    end_date: datetime | None = Query(default=None, description="Filter to date"),
) -> dict:
    """Get summary count by action type (admin only)."""
    service = AdminActionService(db)
    summary = service.get_action_summary(start_date=start_date, end_date=end_date)
    return {"summary": summary}


@actions_router.get(
    "/recent",
    response_model=list[AdminActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Recent Actions",
    description="Get the most recent admin actions. Requires admin role.",
    responses={
        200: {"description": "Recent admin actions"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def get_recent_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    limit: int = Query(default=10, ge=1, le=50, description="Max actions to return"),
) -> list[AdminActionResponse]:
    """Get most recent admin actions (admin only)."""
    service = AdminActionService(db)
    actions = service.get_recent(limit=limit)
    return actions


@actions_router.get(
    "/user/{user_id}",
    response_model=list[AdminActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Actions",
    description="Get all admin actions performed on a specific user. Requires admin role.",
    responses={
        200: {"description": "Actions for user"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def get_user_admin_actions(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[AdminActionResponse]:
    """Get all admin actions performed on a specific user (admin only)."""
    service = AdminActionService(db)
    actions = service.get_user_admin_actions(
        target_user_id=user_id,
        skip=skip,
        limit=limit,
    )
    return actions


@actions_router.get(
    "/resource/{resource_id}",
    response_model=list[AdminActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Resource Actions",
    description="Get all admin actions performed on a specific resource (post, price, etc). Requires admin role.",
    responses={
        200: {"description": "Actions for resource"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def get_resource_admin_actions(
    resource_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[AdminActionResponse]:
    """Get all admin actions performed on a specific resource (admin only)."""
    service = AdminActionService(db)
    actions = service.get_by_resource(
        target_resource_id=resource_id,
        skip=skip,
        limit=limit,
    )
    return actions


@actions_router.get(
    "/type/{action_type}",
    response_model=list[AdminActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Actions by Type",
    description="Get all admin actions of a specific type (user_ban, post_delete, etc). Requires admin role.",
    responses={
        200: {"description": "Actions of type"},
        400: {"description": "Invalid action type"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def get_actions_by_type(
    action_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[AdminActionResponse]:
    """Get all admin actions of a specific type (admin only)."""
    if action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type. Must be one of: {', '.join(VALID_ACTION_TYPES)}",
        )

    service = AdminActionService(db)
    actions = service.get_by_action_type(
        action_type=action_type,
        skip=skip,
        limit=limit,
    )
    return actions


@actions_router.get(
    "/admin/{admin_id}",
    response_model=list[AdminActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Actions by Admin",
    description="Get all actions performed by a specific admin user. Requires admin role.",
    responses={
        200: {"description": "Actions by admin"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def get_actions_by_admin(
    admin_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[AdminActionResponse]:
    """Get all actions performed by a specific admin (admin only)."""
    service = AdminActionService(db)
    actions = service.get_by_admin(
        admin_id=admin_id,
        skip=skip,
        limit=limit,
    )
    return actions


@actions_router.get(
    "/{action_id}",
    response_model=AdminActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Admin Action",
    description="Retrieve a specific admin action by ID. Requires admin role.",
    responses={
        200: {"description": "Action found", "model": AdminActionResponse},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Action not found"},
    }
)
async def get_admin_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> AdminActionResponse:
    """Get a single admin action by ID (admin only)."""
    service = AdminActionService(db)
    action = service.get_by_id(action_id)

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin action not found",
        )

    return action


@actions_router.get(
    "/",
    response_model=AdminActionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Admin Actions",
    description="List all admin actions with optional filtering by admin, type, user, and date range. Requires admin role.",
    responses={
        200: {"description": "Paginated admin actions"},
        400: {"description": "Invalid action type"},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    }
)
async def list_admin_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
    admin_id: UUID | None = Query(default=None, description="Filter by admin"),
    action_type: str | None = Query(default=None, description="Filter by action type"),
    target_user_id: UUID | None = Query(default=None, description="Filter by target user"),
    start_date: datetime | None = Query(default=None, description="Filter from date"),
    end_date: datetime | None = Query(default=None, description="Filter to date"),
) -> AdminActionListResponse:
    """List admin actions with optional filtering (admin only)."""
    # Validate action_type if provided
    if action_type and action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type. Must be one of: {', '.join(VALID_ACTION_TYPES)}",
        )

    service = AdminActionService(db)

    actions = service.get_all(
        skip=skip,
        limit=limit,
        admin_id=admin_id,
        action_type=action_type,
        target_user_id=target_user_id,
        start_date=start_date,
        end_date=end_date,
    )

    total = service.count(
        admin_id=admin_id,
        action_type=action_type,
        target_user_id=target_user_id,
        start_date=start_date,
        end_date=end_date,
    )

    return AdminActionListResponse(
        items=actions,
        total=total,
        skip=skip,
        limit=limit,
    )


# Include actions router as subrouter
router.include_router(actions_router)
