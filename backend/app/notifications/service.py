from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Notification
from app.notifications.schemas import (
    NotificationCreate,
    NotificationUpdate,
    BulkNotificationCreate,
    VALID_NOTIFICATION_TYPES,
)


class NotificationService:
    """Service class for Notification operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification."""
        try:
            notification = Notification(
                user_id=notification_data.user_id,
                title=notification_data.title,
                message=notification_data.message,
                notification_type=notification_data.notification_type,
                related_id=notification_data.related_id,
            )
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            return notification
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, notification_id: UUID) -> Notification | None:
        """Get a single notification by ID."""
        return self.db.query(Notification).filter(
            Notification.id == notification_id,
        ).first()

    def get_user_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_read: bool | None = None,
        notification_type: str | None = None,
    ) -> list[Notification]:
        """Get notifications for a user with optional filtering."""
        query = self.db.query(Notification).filter(Notification.user_id == user_id)

        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        if notification_type:
            if notification_type in VALID_NOTIFICATION_TYPES:
                query = query.filter(Notification.notification_type == notification_type)

        return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    def mark_as_read(self, notification_id: UUID, user_id: UUID | None = None) -> Notification | None:
        """Mark a notification as read."""
        query = self.db.query(Notification).filter(Notification.id == notification_id)

        # If user_id provided, ensure notification belongs to user
        if user_id:
            query = query.filter(Notification.user_id == user_id)

        notification = query.first()

        if not notification:
            return None

        try:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(notification)
            return notification
        except Exception:
            self.db.rollback()
            raise

    def mark_as_unread(self, notification_id: UUID, user_id: UUID | None = None) -> Notification | None:
        """Mark a notification as unread."""
        query = self.db.query(Notification).filter(Notification.id == notification_id)

        if user_id:
            query = query.filter(Notification.user_id == user_id)

        notification = query.first()

        if not notification:
            return None

        try:
            notification.is_read = False
            notification.read_at = None
            self.db.commit()
            self.db.refresh(notification)
            return notification
        except Exception:
            self.db.rollback()
            raise

    def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user. Returns count of updated."""
        try:
            count = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
            ).update({
                "is_read": True,
                "read_at": datetime.now(timezone.utc),
            })
            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

    def delete(self, notification_id: UUID, user_id: UUID | None = None) -> bool:
        """Hard delete a notification."""
        query = self.db.query(Notification).filter(Notification.id == notification_id)

        if user_id:
            query = query.filter(Notification.user_id == user_id)

        notification = query.first()

        if not notification:
            return False

        try:
            self.db.delete(notification)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def delete_all_read(self, user_id: UUID) -> int:
        """Delete all read notifications for a user. Returns count of deleted."""
        try:
            count = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == True,
            ).delete()
            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

    def count(
        self,
        user_id: UUID,
        is_read: bool | None = None,
        notification_type: str | None = None,
    ) -> int:
        """Count notifications for a user with optional filtering."""
        query = self.db.query(Notification).filter(Notification.user_id == user_id)

        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        if notification_type:
            if notification_type in VALID_NOTIFICATION_TYPES:
                query = query.filter(Notification.notification_type == notification_type)

        return query.count()

    def count_unread(self, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        return self.count(user_id=user_id, is_read=False)

    def bulk_create(self, bulk_data: BulkNotificationCreate) -> list[Notification]:
        """Create notifications for multiple users."""
        try:
            notifications = [
                Notification(
                    user_id=user_id,
                    title=bulk_data.title,
                    message=bulk_data.message,
                    notification_type=bulk_data.notification_type,
                    related_id=bulk_data.related_id,
                )
                for user_id in bulk_data.user_ids
            ]
            self.db.add_all(notifications)
            self.db.commit()
            for notification in notifications:
                self.db.refresh(notification)
            return notifications
        except Exception:
            self.db.rollback()
            raise

    def get_by_type(
        self,
        user_id: UUID,
        notification_type: str,
        limit: int = 100,
    ) -> list[Notification]:
        """Get notifications of a specific type for a user."""
        if notification_type not in VALID_NOTIFICATION_TYPES:
            return []

        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.notification_type == notification_type,
        ).order_by(Notification.created_at.desc()).limit(limit).all()