from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import CommunityPost, CommunityReply, CommunityLike, User
from app.community.schemas import CommunityPostCreate, CommunityPostUpdate, VALID_POST_TYPES


class CommunityPostService:
    """Service class for CommunityPost operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, post_data: CommunityPostCreate, user_id: UUID) -> CommunityPost:
        """Create a new community post."""
        try:
            post = CommunityPost(
                title=post_data.title,
                content=post_data.content,
                user_id=user_id,
                post_type=post_data.post_type,
                district=post_data.district,
                image_url=getattr(post_data, "image_url", None),
            )
            self.db.add(post)
            self.db.commit()
            self.db.refresh(post)
            return post
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, post_id: UUID) -> CommunityPost | None:
        """Get a single community post by ID."""
        return self.db.query(CommunityPost).options(joinedload(CommunityPost.user)).filter(
            CommunityPost.id == post_id,
            CommunityPost.deleted_at.is_(None),
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID | None = None,
        post_type: str | None = None,
        district: str | None = None,
    ) -> list[CommunityPost]:
        """Get community posts with optional filtering."""
        query = self.db.query(CommunityPost).options(joinedload(CommunityPost.user)).filter(CommunityPost.deleted_at.is_(None))

        if user_id:
            query = query.filter(CommunityPost.user_id == user_id)

        if post_type:
            if post_type in VALID_POST_TYPES:
                query = query.filter(CommunityPost.post_type == post_type)

        if district:
            query = query.filter(CommunityPost.district == district)

        return query.order_by(
            CommunityPost.is_pinned.desc(),
            CommunityPost.created_at.desc(),
        ).offset(skip).limit(limit).all()

    def get_by_user(self, user_id: UUID, limit: int = 100) -> list[CommunityPost]:
        """Get all posts by a specific user."""
        return self.db.query(CommunityPost).filter(
            CommunityPost.user_id == user_id,
            CommunityPost.deleted_at.is_(None),
        ).order_by(CommunityPost.created_at.desc()).limit(limit).all()

    def get_by_district(self, district: str, limit: int = 100) -> list[CommunityPost]:
        """Get all posts for a specific district."""
        return self.db.query(CommunityPost).filter(
            CommunityPost.district == district,
            CommunityPost.deleted_at.is_(None),
        ).order_by(CommunityPost.created_at.desc()).limit(limit).all()

    def get_by_type(self, post_type: str, limit: int = 100) -> list[CommunityPost]:
        """Get all posts of a specific type."""
        if post_type not in VALID_POST_TYPES:
            return []

        return self.db.query(CommunityPost).filter(
            CommunityPost.post_type == post_type,
            CommunityPost.deleted_at.is_(None),
        ).order_by(CommunityPost.created_at.desc()).limit(limit).all()

    def update(
        self,
        post_id: UUID,
        post_data: CommunityPostUpdate,
        user_id: UUID | None = None,
    ) -> CommunityPost | None:
        """Update an existing community post."""
        query = self.db.query(CommunityPost).filter(
            CommunityPost.id == post_id,
            CommunityPost.deleted_at.is_(None),
        )

        # If user_id provided, ensure only author can update
        if user_id:
            query = query.filter(CommunityPost.user_id == user_id)

        post = query.first()

        if not post:
            return None

        update_data = post_data.model_dump(exclude_unset=True)

        if not update_data:
            return post

        try:
            for field, value in update_data.items():
                setattr(post, field, value)

            self.db.commit()
            self.db.refresh(post)
            return post
        except Exception:
            self.db.rollback()
            raise

    def delete(self, post_id: UUID, user_id: UUID | None = None) -> bool:
        """Soft delete a community post."""
        query = self.db.query(CommunityPost).filter(
            CommunityPost.id == post_id,
            CommunityPost.deleted_at.is_(None),
        )

        # If user_id provided, ensure only author can delete
        if user_id:
            query = query.filter(CommunityPost.user_id == user_id)

        post = query.first()

        if not post:
            return False

        try:
            post.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def restore(self, post_id: UUID) -> CommunityPost | None:
        """Restore a soft-deleted community post."""
        post = self.db.query(CommunityPost).filter(
            CommunityPost.id == post_id,
            CommunityPost.deleted_at.isnot(None),
        ).first()

        if not post:
            return None

        try:
            post.deleted_at = None
            self.db.commit()
            self.db.refresh(post)
            return post
        except Exception:
            self.db.rollback()
            raise

    def count(
        self,
        user_id: UUID | None = None,
        post_type: str | None = None,
        district: str | None = None,
    ) -> int:
        """Count community posts with optional filtering."""
        query = self.db.query(CommunityPost).filter(CommunityPost.deleted_at.is_(None))

        if user_id:
            query = query.filter(CommunityPost.user_id == user_id)

        if post_type:
            if post_type in VALID_POST_TYPES:
                query = query.filter(CommunityPost.post_type == post_type)

        if district:
            query = query.filter(CommunityPost.district == district)

        return query.count()

    def set_admin_override(self, post_id: UUID, is_override: bool) -> CommunityPost | None:
        """Set admin override flag on a post."""
        post = self.db.query(CommunityPost).filter(
            CommunityPost.id == post_id,
            CommunityPost.deleted_at.is_(None),
        ).first()

        if not post:
            return None

        try:
            post.is_admin_override = is_override
            self.db.commit()
            self.db.refresh(post)
            return post
        except Exception:
            self.db.rollback()
            raise

    def is_author(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if a user is the author of a post."""
        post = self.db.query(CommunityPost).filter(
            CommunityPost.id == post_id,
            CommunityPost.user_id == user_id,
            CommunityPost.deleted_at.is_(None),
        ).first()
        return post is not None

    def search(self, query: str, limit: int = 20) -> list[CommunityPost]:
        """Search posts by title or content."""
        search_term = f"%{query.strip()}%"
        return self.db.query(CommunityPost).filter(
            CommunityPost.deleted_at.is_(None),
            (CommunityPost.title.ilike(search_term)) |
            (CommunityPost.content.ilike(search_term))
        ).order_by(CommunityPost.created_at.desc()).limit(limit).all()

    def get_replies(self, post_id: UUID) -> list[CommunityReply]:
        """Get all replies for a post."""
        return self.db.query(CommunityReply).options(
            joinedload(CommunityReply.user)
        ).filter(
            CommunityReply.post_id == post_id
        ).order_by(CommunityReply.created_at.asc()).all()

    def add_reply(self, post_id: UUID, user_id: UUID, content: str) -> CommunityReply:
        """Add a reply to a post."""
        # Ensure post exists
        post = self.get_by_id(post_id)
        if not post:
            raise ValueError("Post not found")

        try:
            reply = CommunityReply(
                post_id=post_id,
                user_id=user_id,
                content=content
            )
            self.db.add(reply)
            self.db.commit()
            self.db.refresh(reply)
            
            # Load the user relationship for the response
            reply = self.db.query(CommunityReply).options(
                joinedload(CommunityReply.user)
            ).filter(CommunityReply.id == reply.id).first()
            
            return reply
        except Exception:
            self.db.rollback()
            raise

    def upvote_post(self, post_id: UUID, user_id: UUID) -> bool:
        """Upvote a post. Returns True if vote added, False if already exists."""
        # Ensure post exists
        if not self.get_by_id(post_id):
            raise ValueError("Post not found")

        # Check existing like
        existing_like = self.db.query(CommunityLike).filter(
            CommunityLike.post_id == post_id,
            CommunityLike.user_id == user_id
        ).first()

        if existing_like:
            return False

        try:
            like = CommunityLike(post_id=post_id, user_id=user_id)
            self.db.add(like)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def remove_upvote(self, post_id: UUID, user_id: UUID) -> bool:
        """Remove upvote from a post. Returns True if removed, False if not found."""
        like = self.db.query(CommunityLike).filter(
            CommunityLike.post_id == post_id,
            CommunityLike.user_id == user_id
        ).first()

        if not like:
            return False

        try:
            self.db.delete(like)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def has_user_liked(self, post_id: UUID, user_id: UUID) -> bool:
        """Check if a user has liked a specific post."""
        return self.db.query(CommunityLike).filter(
            CommunityLike.post_id == post_id,
            CommunityLike.user_id == user_id
        ).first() is not None

    def increment_view_count(self, post_id: UUID) -> None:
        """Increment view count for a post (fire-and-forget)."""
        try:
            self.db.query(CommunityPost).filter(
                CommunityPost.id == post_id
            ).update({"view_count": CommunityPost.view_count + 1})
            self.db.commit()
        except Exception:
            self.db.rollback()

    def set_pinned(self, post_id: UUID, is_pinned: bool) -> CommunityPost | None:
        """Pin or unpin a post (admin only)."""
        post = self.db.query(CommunityPost).filter(
            CommunityPost.id == post_id,
            CommunityPost.deleted_at.is_(None),
        ).first()

        if not post:
            return None

        try:
            post.is_pinned = is_pinned
            self.db.commit()
            self.db.refresh(post)
            return post
        except Exception:
            self.db.rollback()
            raise