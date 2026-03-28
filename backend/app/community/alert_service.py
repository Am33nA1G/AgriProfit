"""
Alert notification service for community posts.

When a user creates an 'alert' type post, this service creates notifications
for all users in the same district + neighboring districts. This enables
farmers to share time-sensitive information (pest outbreaks, weather warnings,
market disruptions) with relevant neighbors.
"""
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import User, CommunityPost, Notification
from app.community.district_neighbors import get_target_districts

logger = logging.getLogger(__name__)


class AlertNotificationService:
    """Creates targeted notifications when alert posts are published."""

    def __init__(self, db: Session):
        self.db = db

    def create_alert_notifications(
        self,
        post: CommunityPost,
        author: User,
    ) -> int:
        """
        Create notifications for users in the author's district and neighbors.

        Args:
            post: The alert community post
            author: The post author

        Returns:
            Number of notifications created
        """
        if post.post_type != "alert":
            return 0

        author_district = author.district
        author_state = author.state

        if not author_district or not author_state:
            logger.warning(
                "Alert post %s created by user without district/state info", post.id
            )
            return 0

        # Get target districts (own + neighbors)
        target_districts = get_target_districts(author_district, author_state)

        # Find active, non-banned users in target districts (excluding author)
        target_users = (
            self.db.query(User)
            .filter(
                User.district.in_(target_districts),
                User.state == author_state,
                User.id != author.id,
                User.is_banned == False,
                User.deleted_at.is_(None),
            )
            .all()
        )

        if not target_users:
            logger.info(
                "Alert post %s: no users found in target districts %s",
                post.id,
                target_districts,
            )
            return 0

        # Create notification for each user
        title_preview = post.title[:50] + ("..." if len(post.title) > 50 else "")
        content_preview = post.content[:100] + ("..." if len(post.content) > 100 else "")

        notifications = []
        for user in target_users:
            notification = Notification(
                user_id=user.id,
                post_id=post.id,
                notification_type="community",
                title=f"ALERT: {title_preview}",
                message=f"Alert from {author_district}: {content_preview}",
            )
            notifications.append(notification)

        self.db.add_all(notifications)
        self.db.commit()

        count = len(notifications)
        logger.info(
            "Alert post %s: created %d notifications across %d districts",
            post.id,
            count,
            len(target_districts),
        )
        return count

    def get_alert_status(
        self,
        post: CommunityPost,
        current_user: User,
    ) -> dict:
        """
        Check whether an alert post should be highlighted for a specific user.

        Returns:
            Dict with is_alert, should_highlight, in_affected_area, author_district
        """
        if post.post_type != "alert":
            return {
                "is_alert": False,
                "should_highlight": False,
                "in_affected_area": False,
                "author_district": None,
            }

        # Get the post author
        author = self.db.query(User).filter(User.id == post.user_id).first()
        if not author or not author.district or not author.state:
            return {
                "is_alert": True,
                "should_highlight": False,
                "in_affected_area": False,
                "author_district": None,
            }

        target_districts = get_target_districts(author.district, author.state)

        in_affected_area = (
            current_user.district in target_districts
            and current_user.state == author.state
        ) if current_user.district and current_user.state else False

        return {
            "is_alert": True,
            "should_highlight": in_affected_area,
            "in_affected_area": in_affected_area,
            "author_district": author.district,
        }
