import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.admin.service import AdminActionService
from app.admin.schemas import AdminActionCreate
from tests.utils import create_test_user


class TestAdminServiceEdgeCases:
    """Edge case tests for AdminActionService."""

    def test_get_by_id_nonexistent(self, test_db):
        """Test getting non-existent admin action returns None."""
        service = AdminActionService(test_db)
        result = service.get_by_id(uuid4())
        assert result is None

    def test_get_by_id_success(self, test_db):
        """Test getting admin action by ID."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        action = service.create(
            AdminActionCreate(
                action_type="user_ban",
                description="Banned user for spam",
            ),
            admin_id=admin.id,
        )

        result = service.get_by_id(action.id)
        assert result is not None
        assert result.id == action.id

    def test_filter_by_action_type(self, test_db):
        """Test filtering admin actions by action_type."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(
                action_type="user_ban",
                description="Banned user for spam",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="post_delete",
                description="Deleted inappropriate post",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="user_ban",
                description="Banned another user",
            ),
            admin_id=admin.id,
        )

        results = service.get_all(action_type="user_ban")
        assert len(results) == 2
        for action in results:
            assert action.action_type == "user_ban"

    def test_filter_by_invalid_action_type(self, test_db):
        """Test filtering by invalid action_type returns all."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(
                action_type="user_ban",
                description="Banned user for spam",
            ),
            admin_id=admin.id,
        )

        # Invalid type should be ignored
        results = service.get_all(action_type="invalid_type")
        assert len(results) == 1

    def test_filter_by_target_user_id(self, test_db):
        """Test filtering admin actions by target_user_id."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        target_user = create_test_user(test_db, phone_number="9876543211")
        other_user = create_test_user(test_db, phone_number="9876543212")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=target_user.id,
                description="Banned target user",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=other_user.id,
                description="Banned other user",
            ),
            admin_id=admin.id,
        )

        results = service.get_all(target_user_id=target_user.id)
        assert len(results) == 1
        assert results[0].target_user_id == target_user.id

    def test_multiple_filters_combined(self, test_db):
        """Test combining multiple filters."""
        admin1 = create_test_user(test_db, phone_number="9876543210", role="admin")
        admin2 = create_test_user(test_db, phone_number="9876543211", role="admin")
        target = create_test_user(test_db, phone_number="9876543212")
        service = AdminActionService(test_db)

        # Create various actions
        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=target.id,
                description="Admin1 banned target",
            ),
            admin_id=admin1.id,
        )
        service.create(
            AdminActionCreate(
                action_type="post_delete",
                target_user_id=target.id,
                description="Admin1 deleted post",
            ),
            admin_id=admin1.id,
        )
        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=target.id,
                description="Admin2 banned target",
            ),
            admin_id=admin2.id,
        )

        # Filter by admin_id + action_type
        results = service.get_all(admin_id=admin1.id, action_type="user_ban")
        assert len(results) == 1
        assert results[0].admin_id == admin1.id
        assert results[0].action_type == "user_ban"

    def test_create_with_metadata(self, test_db):
        """Test creating admin action with metadata."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        metadata = {
            "reason": "Spam violation",
            "previous_warnings": 3,
            "ban_duration_days": 7,
        }

        action = service.create(
            AdminActionCreate(
                action_type="user_ban",
                description="Banned user for repeated spam",
                action_metadata=metadata,
            ),
            admin_id=admin.id,
        )

        assert action.action_metadata is not None
        assert action.action_metadata["reason"] == "Spam violation"
        assert action.action_metadata["previous_warnings"] == 3

    def test_create_with_target_resource_id(self, test_db):
        """Test creating admin action with target_resource_id."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)
        resource_id = uuid4()

        action = service.create(
            AdminActionCreate(
                action_type="post_delete",
                target_resource_id=resource_id,
                description="Deleted post for policy violation",
            ),
            admin_id=admin.id,
        )

        assert action.target_resource_id == resource_id

    def test_get_by_admin(self, test_db):
        """Test getting all actions by a specific admin."""
        admin1 = create_test_user(test_db, phone_number="9876543210", role="admin")
        admin2 = create_test_user(test_db, phone_number="9876543211", role="admin")
        service = AdminActionService(test_db)

        # Create actions for both admins
        for i in range(3):
            service.create(
                AdminActionCreate(
                    action_type="user_ban",
                    description=f"Admin1 action {i}",
                ),
                admin_id=admin1.id,
            )
        for i in range(2):
            service.create(
                AdminActionCreate(
                    action_type="post_delete",
                    description=f"Admin2 action {i}",
                ),
                admin_id=admin2.id,
            )

        results = service.get_by_admin(admin1.id)
        assert len(results) == 3
        for action in results:
            assert action.admin_id == admin1.id

    def test_get_user_admin_actions(self, test_db):
        """Test getting all actions targeting a specific user."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        target = create_test_user(test_db, phone_number="9876543211")
        other = create_test_user(test_db, phone_number="9876543212")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=target.id,
                description="Banned target",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="user_unban",
                target_user_id=target.id,
                description="Unbanned target",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=other.id,
                description="Banned other",
            ),
            admin_id=admin.id,
        )

        results = service.get_user_admin_actions(target.id)
        assert len(results) == 2
        for action in results:
            assert action.target_user_id == target.id

    def test_get_by_action_type(self, test_db):
        """Test getting actions by type."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(action_type="user_ban", description="Ban action"),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(action_type="post_delete", description="Delete action"),
            admin_id=admin.id,
        )

        results = service.get_by_action_type("user_ban")
        assert len(results) == 1
        assert results[0].action_type == "user_ban"

    def test_get_by_action_type_invalid(self, test_db):
        """Test getting actions by invalid type returns empty."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(action_type="user_ban", description="Ban action"),
            admin_id=admin.id,
        )

        results = service.get_by_action_type("invalid_type")
        assert len(results) == 0

    def test_get_by_resource(self, test_db):
        """Test getting actions by target resource ID."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)
        resource1 = uuid4()
        resource2 = uuid4()

        service.create(
            AdminActionCreate(
                action_type="post_delete",
                target_resource_id=resource1,
                description="Deleted resource 1",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="post_restore",
                target_resource_id=resource1,
                description="Restored resource 1",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="post_delete",
                target_resource_id=resource2,
                description="Deleted resource 2",
            ),
            admin_id=admin.id,
        )

        results = service.get_by_resource(resource1)
        assert len(results) == 2
        for action in results:
            assert action.target_resource_id == resource1

    def test_count_with_filters(self, test_db):
        """Test counting actions with various filters."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        target = create_test_user(test_db, phone_number="9876543211")
        service = AdminActionService(test_db)

        service.create(
            AdminActionCreate(
                action_type="user_ban",
                target_user_id=target.id,
                description="Action 1",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="user_ban",
                description="Action 2",
            ),
            admin_id=admin.id,
        )
        service.create(
            AdminActionCreate(
                action_type="post_delete",
                description="Action 3",
            ),
            admin_id=admin.id,
        )

        assert service.count() == 3
        assert service.count(admin_id=admin.id) == 3
        assert service.count(action_type="user_ban") == 2
        assert service.count(target_user_id=target.id) == 1
        assert service.count(action_type="invalid_type") == 3  # Invalid ignored

    def test_get_recent(self, test_db):
        """Test getting most recent actions."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        for i in range(5):
            service.create(
                AdminActionCreate(
                    action_type="user_ban",
                    description=f"Action {i}",
                ),
                admin_id=admin.id,
            )

        results = service.get_recent(limit=3)
        assert len(results) == 3

    def test_get_action_summary(self, test_db):
        """Test getting action type summary."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        # Create actions of different types
        for _ in range(3):
            service.create(
                AdminActionCreate(action_type="user_ban", description="Banned user for violation"),
                admin_id=admin.id,
            )
        for _ in range(2):
            service.create(
                AdminActionCreate(action_type="post_delete", description="Deleted post for policy"),
                admin_id=admin.id,
            )
        service.create(
            AdminActionCreate(action_type="user_unban", description="Unbanned user after review"),
            admin_id=admin.id,
        )

        summary = service.get_action_summary()
        assert summary["user_ban"] == 3
        assert summary["post_delete"] == 2
        assert summary["user_unban"] == 1

    def test_log_action_convenience_method(self, test_db):
        """Test the log_action convenience method."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        target = create_test_user(test_db, phone_number="9876543211")
        service = AdminActionService(test_db)
        resource_id = uuid4()

        action = service.log_action(
            admin_id=admin.id,
            action_type="price_update",
            description="Updated commodity price",
            target_user_id=target.id,
            target_resource_id=resource_id,
            metadata={"old_price": 100, "new_price": 150},
        )

        assert action is not None
        assert action.admin_id == admin.id
        assert action.action_type == "price_update"
        assert action.target_user_id == target.id
        assert action.target_resource_id == resource_id

    def test_pagination(self, test_db):
        """Test pagination in get_all."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        # Create 10 actions
        for i in range(10):
            service.create(
                AdminActionCreate(
                    action_type="user_ban",
                    description=f"Action {i}",
                ),
                admin_id=admin.id,
            )

        # Get first page
        page1 = service.get_all(skip=0, limit=3)
        assert len(page1) == 3

        # Get second page
        page2 = service.get_all(skip=3, limit=3)
        assert len(page2) == 3

        # Verify different results
        page1_ids = {a.id for a in page1}
        page2_ids = {a.id for a in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_date_range_filter(self, test_db):
        """Test filtering by date range."""
        admin = create_test_user(test_db, phone_number="9876543210", role="admin")
        service = AdminActionService(test_db)

        # Create action
        service.create(
            AdminActionCreate(action_type="user_ban", description="Test action"),
            admin_id=admin.id,
        )

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Filter with date range that includes the action
        results = service.get_all(start_date=yesterday, end_date=tomorrow)
        assert len(results) == 1

        # Filter with future date range
        future = now + timedelta(days=10)
        results = service.get_all(start_date=future)
        assert len(results) == 0
