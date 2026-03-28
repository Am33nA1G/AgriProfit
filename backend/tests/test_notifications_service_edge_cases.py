import pytest
from uuid import uuid4
from datetime import datetime

from app.notifications.service import NotificationService
from app.notifications.schemas import NotificationCreate, BulkNotificationCreate
from tests.utils import create_test_user


class TestNotificationServiceEdgeCases:
    """Edge case tests for NotificationService."""

    def test_mark_as_read_nonexistent(self, test_db):
        """Test marking non-existent notification as read returns None."""
        service = NotificationService(test_db)
        result = service.mark_as_read(uuid4())
        assert result is None

    def test_mark_as_read_wrong_user(self, test_db):
        """Test marking notification as read by wrong user returns None."""
        user = create_test_user(test_db, phone_number="9876543210")
        other_user = create_test_user(test_db, phone_number="9876543211")
        service = NotificationService(test_db)

        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))

        # Try to mark as read by wrong user
        result = service.mark_as_read(notification.id, user_id=other_user.id)
        assert result is None

    def test_mark_as_unread_nonexistent(self, test_db):
        """Test marking non-existent notification as unread returns None."""
        service = NotificationService(test_db)
        result = service.mark_as_unread(uuid4())
        assert result is None

    def test_mark_as_unread_wrong_user(self, test_db):
        """Test marking notification as unread by wrong user returns None."""
        user = create_test_user(test_db, phone_number="9876543210")
        other_user = create_test_user(test_db, phone_number="9876543211")
        service = NotificationService(test_db)

        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))

        # Mark as read first
        service.mark_as_read(notification.id)

        # Try to mark as unread by wrong user
        result = service.mark_as_unread(notification.id, user_id=other_user.id)
        assert result is None

    def test_mark_all_as_read_no_unread(self, test_db):
        """Test mark all as read when no unread notifications exist."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        # Create notification and mark as read
        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))
        service.mark_as_read(notification.id)

        # Try to mark all as read again
        count = service.mark_all_as_read(user.id)
        assert count == 0

    def test_mark_all_as_read_multiple(self, test_db):
        """Test mark all as read with multiple unread notifications."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        # Create multiple notifications
        for i in range(3):
            service.create(NotificationCreate(
                user_id=user.id,
                title=f"Test Notification {i}",
                message="Test message content",
                notification_type="system",
            ))

        count = service.mark_all_as_read(user.id)
        assert count == 3

    def test_delete_nonexistent(self, test_db):
        """Test deleting non-existent notification returns False."""
        service = NotificationService(test_db)
        result = service.delete(uuid4())
        assert result is False

    def test_delete_wrong_user(self, test_db):
        """Test deleting notification by wrong user returns False."""
        user = create_test_user(test_db, phone_number="9876543210")
        other_user = create_test_user(test_db, phone_number="9876543211")
        service = NotificationService(test_db)

        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))

        result = service.delete(notification.id, user_id=other_user.id)
        assert result is False
        # Verify notification still exists
        assert service.get_by_id(notification.id) is not None

    def test_get_notifications_with_is_read_filter_true(self, test_db):
        """Test filtering notifications by is_read=True."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        # Create read and unread notifications
        n1 = service.create(NotificationCreate(
            user_id=user.id,
            title="Read Notification",
            message="Test message content",
            notification_type="system",
        ))
        service.mark_as_read(n1.id)

        service.create(NotificationCreate(
            user_id=user.id,
            title="Unread Notification",
            message="Test message content",
            notification_type="system",
        ))

        results = service.get_user_notifications(user.id, is_read=True)
        assert len(results) == 1
        assert results[0].title == "Read Notification"

    def test_get_notifications_with_is_read_filter_false(self, test_db):
        """Test filtering notifications by is_read=False."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        n1 = service.create(NotificationCreate(
            user_id=user.id,
            title="Read Notification",
            message="Test message content",
            notification_type="system",
        ))
        service.mark_as_read(n1.id)

        service.create(NotificationCreate(
            user_id=user.id,
            title="Unread Notification",
            message="Test message content",
            notification_type="system",
        ))

        results = service.get_user_notifications(user.id, is_read=False)
        assert len(results) == 1
        assert results[0].title == "Unread Notification"

    def test_get_notifications_with_type_filter(self, test_db):
        """Test filtering notifications by notification_type."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        service.create(NotificationCreate(
            user_id=user.id,
            title="System Notification",
            message="Test message content",
            notification_type="system",
        ))
        service.create(NotificationCreate(
            user_id=user.id,
            title="Price Alert",
            message="Test message content",
            notification_type="price_alert",
        ))

        results = service.get_user_notifications(user.id, notification_type="price_alert")
        assert len(results) == 1
        assert results[0].title == "Price Alert"

    def test_get_notifications_invalid_type_filter(self, test_db):
        """Test filtering notifications with invalid type returns all."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        service.create(NotificationCreate(
            user_id=user.id,
            title="System Notification",
            message="Test message content",
            notification_type="system",
        ))

        # Invalid type should be ignored and return all notifications
        results = service.get_user_notifications(user.id, notification_type="invalid_type")
        assert len(results) == 1

    def test_create_notification_with_related_id(self, test_db):
        """Test creating notification with all optional fields including related_id."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)
        related_id = uuid4()

        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="price_alert",
            related_id=related_id,
        ))

        assert notification.related_id == related_id
        assert notification.notification_type == "price_alert"

    def test_count_unread(self, test_db):
        """Test counting unread notifications."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        # Create 3 notifications, mark 1 as read
        for i in range(3):
            service.create(NotificationCreate(
                user_id=user.id,
                title=f"Test Notification {i}",
                message="Test message content",
                notification_type="system",
            ))

        n = service.get_user_notifications(user.id)[0]
        service.mark_as_read(n.id)

        assert service.count_unread(user.id) == 2

    def test_count_with_filters(self, test_db):
        """Test count with is_read and notification_type filters."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        n1 = service.create(NotificationCreate(
            user_id=user.id,
            title="System Read",
            message="Test message content",
            notification_type="system",
        ))
        service.mark_as_read(n1.id)

        service.create(NotificationCreate(
            user_id=user.id,
            title="System Unread",
            message="Test message content",
            notification_type="system",
        ))

        service.create(NotificationCreate(
            user_id=user.id,
            title="Price Alert",
            message="Test message content",
            notification_type="price_alert",
        ))

        assert service.count(user.id, is_read=True) == 1
        assert service.count(user.id, is_read=False) == 2
        assert service.count(user.id, notification_type="system") == 2
        assert service.count(user.id, notification_type="invalid") == 3  # Invalid type ignored

    def test_delete_all_read(self, test_db):
        """Test deleting all read notifications."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        # Create notifications and mark some as read
        n1 = service.create(NotificationCreate(
            user_id=user.id,
            title="Read 1",
            message="Test message content",
            notification_type="system",
        ))
        n2 = service.create(NotificationCreate(
            user_id=user.id,
            title="Read 2",
            message="Test message content",
            notification_type="system",
        ))
        service.create(NotificationCreate(
            user_id=user.id,
            title="Unread",
            message="Test message content",
            notification_type="system",
        ))

        service.mark_as_read(n1.id)
        service.mark_as_read(n2.id)

        count = service.delete_all_read(user.id)
        assert count == 2

        # Verify only unread remains
        remaining = service.get_user_notifications(user.id)
        assert len(remaining) == 1
        assert remaining[0].title == "Unread"

    def test_bulk_create(self, test_db):
        """Test creating notifications for multiple users."""
        user1 = create_test_user(test_db, phone_number="9876543210")
        user2 = create_test_user(test_db, phone_number="9876543211")
        user3 = create_test_user(test_db, phone_number="9876543212")
        service = NotificationService(test_db)

        notifications = service.bulk_create(BulkNotificationCreate(
            user_ids=[user1.id, user2.id, user3.id],
            title="Bulk Notification",
            message="Message for all users",
            notification_type="announcement",
        ))

        assert len(notifications) == 3

        # Verify each user got notification
        assert len(service.get_user_notifications(user1.id)) == 1
        assert len(service.get_user_notifications(user2.id)) == 1
        assert len(service.get_user_notifications(user3.id)) == 1

    def test_get_by_type_valid(self, test_db):
        """Test getting notifications by valid type."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        service.create(NotificationCreate(
            user_id=user.id,
            title="Forecast Notification",
            message="Test message content",
            notification_type="forecast",
        ))
        service.create(NotificationCreate(
            user_id=user.id,
            title="System Notification",
            message="Test message content",
            notification_type="system",
        ))

        results = service.get_by_type(user.id, "forecast")
        assert len(results) == 1
        assert results[0].notification_type == "forecast"

    def test_get_by_type_invalid(self, test_db):
        """Test getting notifications by invalid type returns empty."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))

        results = service.get_by_type(user.id, "invalid_type")
        assert len(results) == 0

    def test_get_by_id_nonexistent(self, test_db):
        """Test getting non-existent notification by ID."""
        service = NotificationService(test_db)
        result = service.get_by_id(uuid4())
        assert result is None

    def test_mark_as_read_success(self, test_db):
        """Test successfully marking notification as read."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))

        assert notification.is_read is False
        assert notification.read_at is None

        result = service.mark_as_read(notification.id)
        assert result is not None
        assert result.is_read is True
        assert result.read_at is not None

    def test_mark_as_unread_success(self, test_db):
        """Test successfully marking notification as unread."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = NotificationService(test_db)

        notification = service.create(NotificationCreate(
            user_id=user.id,
            title="Test Notification",
            message="Test message content",
            notification_type="system",
        ))

        service.mark_as_read(notification.id)
        result = service.mark_as_unread(notification.id)

        assert result is not None
        assert result.is_read is False
        assert result.read_at is None
