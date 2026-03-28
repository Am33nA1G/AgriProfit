"""
Community Post routes for user-generated content.

This module provides endpoints for:
- Creating, updating, and deleting posts (authenticated users)
- Searching and filtering posts (public)
- Admin moderation features (admin only)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User
from app.community.schemas import (
    CommunityPostCreate,
    CommunityPostUpdate,
    CommunityPostResponse,
    CommunityPostListResponse,
    CommunityReplyCreate,
    CommunityReplyResponse,
    AlertStatusResponse,
    VALID_POST_TYPES,
)
from app.community.service import CommunityPostService
from app.community.alert_service import AlertNotificationService
from app.auth.security import get_current_user, get_current_user_optional, require_role
from app.core.rate_limit import limiter, RATE_LIMIT_READ, RATE_LIMIT_WRITE

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/community/posts", tags=["Community"])


@router.post(
    "/",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Post",
    description="Create a new community post. Requires authentication.",
    responses={
        201: {"description": "Post created", "model": CommunityPostResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
    }
)
async def create_post(
    post_data: CommunityPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityPostResponse:
    """Create a new community post (requires authentication).

    If post_type is 'alert', notifications are sent to users in the
    author's district and neighboring districts.
    """
    service = CommunityPostService(db)
    try:
        post = service.create(post_data, user_id=current_user.id)

        # If alert post, create notifications for neighboring districts
        notifications_sent = 0
        if post.post_type == "alert":
            alert_service = AlertNotificationService(db)
            notifications_sent = alert_service.create_alert_notifications(post, current_user)
            logger.info(
                "Alert post %s created by user %s: %d notifications sent",
                post.id, current_user.id, notifications_sent,
            )

        # Enrich with author name
        response_dict = {**post.__dict__}
        response_dict['author_name'] = current_user.name
        return CommunityPostResponse(**response_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/search",
    response_model=list[CommunityPostResponse],
    status_code=status.HTTP_200_OK,
    summary="Search Posts",
    description="Search community posts by title or content. Public endpoint.",
    responses={200: {"description": "Search results"}},
)
async def search_posts(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(default=20, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db),
) -> list[CommunityPostResponse]:
    """Search posts by title or content."""
    service = CommunityPostService(db)
    posts = service.search(query=q, limit=limit)
    return posts


@router.get(
    "/{post_id}",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Post",
    description="Retrieve a specific community post by ID. Public endpoint.",
    responses={
        200: {"description": "Post found", "model": CommunityPostResponse},
        404: {"description": "Post not found"},
    }
)
async def get_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> CommunityPostResponse:
    """Get a single community post by ID. Increments view count."""
    service = CommunityPostService(db)
    post = service.get_by_id(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Build response dict BEFORE incrementing view count.
    # increment_view_count calls db.commit(), which expires the post object and
    # clears its __dict__ — capturing state first prevents a Pydantic ValidationError.
    post_dict = {**post.__dict__}
    post_dict["view_count"] = (post.view_count or 0) + 1  # anticipate the increment
    if hasattr(post, 'user') and post.user:
        post_dict['author_name'] = post.user.name

    # Increment view count (commits session — expires post, but we've already captured state)
    service.increment_view_count(post_id)

    response = CommunityPostResponse(**post_dict)
    if current_user:
        response.user_has_liked = service.has_user_liked(post_id, current_user.id)

        # Add alert highlight status
        if post.post_type == "alert":
            alert_service = AlertNotificationService(db)
            alert_status = alert_service.get_alert_status(post, current_user)
            response.alert_highlight = alert_status["should_highlight"]

    return response


@router.get(
    "/",
    response_model=CommunityPostListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Posts",
    description="List community posts with optional filtering by user, type, and district. Public endpoint.",
    responses={200: {"description": "Paginated posts"}},
)
async def list_posts(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
    user_id: UUID | None = Query(default=None, description="Filter by author"),
    post_type: str | None = Query(default=None, description="Filter by type (discussion, question, tip, announcement, alert)"),
    district: str | None = Query(default=None, description="Filter by district code"),
    current_user: User | None = Depends(get_current_user_optional),
) -> CommunityPostListResponse:
    """List community posts with optional filtering."""
    # Validate post_type if provided
    if post_type and post_type not in VALID_POST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid post_type. Must be one of: {', '.join(VALID_POST_TYPES)}",
        )

    service = CommunityPostService(db)

    posts = service.get_all(
        skip=skip,
        limit=limit,
        user_id=user_id,
        post_type=post_type,
        district=district,
    )

    # Enrich posts with author names and alert status
    alert_service = AlertNotificationService(db) if current_user else None
    enriched_posts = []
    for post in posts:
        post_dict = {**post.__dict__}
        # Get author name from the joined user relationship
        if hasattr(post, 'user') and post.user:
            post_dict['author_name'] = post.user.name

        # Add alert highlight for alert posts if user is logged in
        if post.post_type == "alert" and alert_service and current_user:
            alert_status = alert_service.get_alert_status(post, current_user)
            post_dict["alert_highlight"] = alert_status["should_highlight"]

        enriched_posts.append(CommunityPostResponse(**post_dict))

    total = service.count(
        user_id=user_id,
        post_type=post_type,
        district=district,
    )

    return CommunityPostListResponse(
        items=enriched_posts,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/user/{user_id}",
    response_model=list[CommunityPostResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Posts by User",
    description="Get all posts created by a specific user. Public endpoint.",
    responses={200: {"description": "List of posts"}},
)
async def get_posts_by_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[CommunityPostResponse]:
    """Get all posts by a specific user."""
    service = CommunityPostService(db)
    posts = service.get_by_user(user_id=user_id, limit=limit)
    return posts


@router.get(
    "/district/{district}",
    response_model=list[CommunityPostResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Posts by District",
    description="Get all posts related to a specific district. Public endpoint.",
    responses={200: {"description": "List of posts"}},
)
async def get_posts_by_district(
    district: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[CommunityPostResponse]:
    """Get all posts for a specific district."""
    service = CommunityPostService(db)
    posts = service.get_by_district(district=district, limit=limit)
    return posts


@router.get(
    "/type/{post_type}",
    response_model=list[CommunityPostResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Posts by Type",
    description="Get all posts of a specific type (discussion, question, tip, announcement). Public endpoint.",
    responses={
        200: {"description": "List of posts"},
        400: {"description": "Invalid post type"},
    }
)
async def get_posts_by_type(
    post_type: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=100, description="Max records"),
) -> list[CommunityPostResponse]:
    """Get all posts of a specific type."""
    if post_type not in VALID_POST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid post_type. Must be one of: {', '.join(VALID_POST_TYPES)}",
        )

    service = CommunityPostService(db)
    posts = service.get_by_type(post_type=post_type, limit=limit)
    return posts


@router.put(
    "/{post_id}",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Post",
    description="Update an existing community post. Only the author or admin can update.",
    responses={
        200: {"description": "Post updated", "model": CommunityPostResponse},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not author or admin)"},
        404: {"description": "Post not found"},
    }
)
async def update_post(
    post_id: UUID,
    post_data: CommunityPostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommunityPostResponse:
    """Update an existing community post (author or admin only)."""
    service = CommunityPostService(db)

    # Check if post exists
    existing_post = service.get_by_id(post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Check if user is author or admin
    if existing_post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own posts",
        )

    update_data = post_data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )

    # Only admin can set is_admin_override
    if "is_admin_override" in update_data and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can set admin override flag",
        )

    try:
        post = service.update(post_id, post_data)
        return post
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Post",
    description="Delete a community post. Only the author or admin can delete.",
    responses={
        204: {"description": "Post deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized (not author or admin)"},
        404: {"description": "Post not found"},
    }
)
async def delete_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a community post (author or admin only)."""
    service = CommunityPostService(db)

    # Check if post exists
    existing_post = service.get_by_id(post_id)
    if not existing_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Check if user is author or admin
    if existing_post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts",
        )

    deleted = service.delete(post_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )


@router.post(
    "/{post_id}/admin-override",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_200_OK,
    summary="Set Admin Override (Admin)",
    description="Set admin override flag on a post for moderation. Requires admin role.",
    responses={
        200: {"description": "Override set", "model": CommunityPostResponse},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Post not found"},
    }
)
async def set_admin_override(
    post_id: UUID,
    is_override: bool = Query(..., description="Set admin override flag"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> CommunityPostResponse:
    """Set admin override flag on a post (admin only)."""
    service = CommunityPostService(db)
    post = service.set_admin_override(post_id, is_override)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post


@router.post(
    "/{post_id}/restore",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Post (Admin)",
    description="Restore a soft-deleted community post. Requires admin role.",
    responses={
        200: {"description": "Post restored", "model": CommunityPostResponse},
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
        404: {"description": "Deleted post not found"},
    }
)
async def restore_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> CommunityPostResponse:
    """Restore a soft-deleted post (admin only)."""
    service = CommunityPostService(db)
    post = service.restore(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted post not found",
        )
    return post


@router.get(
    "/{post_id}/replies",
    response_model=list[CommunityReplyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Replies",
    description="Get all replies for a community post. Public endpoint.",
    responses={
        200: {"description": "List of replies"},
        404: {"description": "Post not found"},
    }
)
async def get_replies(
    post_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all replies for a post."""
    service = CommunityPostService(db)
    
    # Verify post exists
    post = service.get_by_id(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    replies = service.get_replies(post_id)
    
    # Construct response using Pydantic models for proper serialization
    return [
        CommunityReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            user_id=reply.user_id,
            content=reply.content,
            created_at=reply.created_at,
            author_name=getattr(reply.user, 'name', None)
        )
        for reply in replies
    ]


@router.post(
    "/{post_id}/reply",
    response_model=CommunityReplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Reply",
    description="Add a reply to a community post. Requires authentication.",
)
async def add_reply(
    post_id: UUID,
    reply_data: CommunityReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a reply to a post."""
    service = CommunityPostService(db)
    try:
        reply = service.add_reply(
            post_id=post_id,
            user_id=current_user.id,
            content=reply_data.content
        )
        # Construct response using Pydantic model for proper serialization
        return CommunityReplyResponse(
            id=reply.id,
            post_id=reply.post_id,
            user_id=reply.user_id,
            content=reply.content,
            created_at=reply.created_at,
            author_name=getattr(reply.user, 'name', None) or current_user.name
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{post_id}/alert-status",
    response_model=AlertStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Alert Status",
    description="Check if an alert post should be highlighted for the current user based on district proximity.",
    responses={
        200: {"description": "Alert status", "model": AlertStatusResponse},
        404: {"description": "Post not found"},
    }
)
async def get_alert_status(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertStatusResponse:
    """Check if an alert post affects the current user's area."""
    service = CommunityPostService(db)
    post = service.get_by_id(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    alert_service = AlertNotificationService(db)
    result = alert_service.get_alert_status(post, current_user)
    return AlertStatusResponse(**result)


@router.post(
    "/{post_id}/pin",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_200_OK,
    summary="Pin Post (Admin)",
    description="Pin or unpin a community post. Pinned posts appear first. Requires admin role.",
    responses={
        200: {"description": "Post pinned/unpinned", "model": CommunityPostResponse},
        403: {"description": "Admin role required"},
        404: {"description": "Post not found"},
    }
)
async def pin_post(
    post_id: UUID,
    is_pinned: bool = Query(..., description="Pin (true) or unpin (false)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> CommunityPostResponse:
    """Pin or unpin a post (admin only)."""
    service = CommunityPostService(db)
    post = service.set_pinned(post_id, is_pinned)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post


@router.post(
    "/{post_id}/upvote",
    status_code=status.HTTP_200_OK,
    summary="Upvote Post",
    description="Upvote a community post. Idempotent (does nothing if already upvoted).",
)
async def upvote_post(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upvote a post."""
    service = CommunityPostService(db)
    try:
        service.upvote_post(post_id, current_user.id)
        return {"message": "Post upvoted"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{post_id}/upvote",
    status_code=status.HTTP_200_OK,
    summary="Remove Upvote",
    description="Remove upvote from a community post.",
)
async def remove_upvote(
    post_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove upvote from a post."""
    service = CommunityPostService(db)
    service.remove_upvote(post_id, current_user.id)
    return {"message": "Upvote removed"}