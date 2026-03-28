import pytest
from uuid import uuid4

from tests.utils import create_test_user
from app.users.service import UserService
from app.users.schemas import UserUpdate


class TestUserService:
    """Tests for User CRUD operations."""

    def test_create_user(self, test_db):
        """Test user creation with valid data."""
        service = UserService(test_db)
        
        user = service.create(
            phone_number="9876543210",
            role="farmer",
            district="KL-TVM",
        )
        
        assert user is not None
        assert user.id is not None
        assert user.phone_number == "9876543210"
        assert user.role == "farmer"
        assert user.district == "KL-TVM"
        assert user.created_at is not None

    def test_create_user_duplicate_phone(self, test_db):
        """Test that creating user with duplicate phone raises error."""
        service = UserService(test_db)
        
        # Create first user
        service.create(
            phone_number="9876543210",
            role="farmer",
            district="KL-TVM",
        )
        
        # Try to create second user with same phone
        with pytest.raises(Exception):
            service.create(
                phone_number="9876543210",
                role="farmer",
                district="KL-KLM",
            )

    def test_get_user_by_id(self, test_db):
        """Test retrieving user by ID."""
        # Create a test user
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        retrieved_user = service.get_by_id(user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.phone_number == user.phone_number
        assert retrieved_user.role == user.role

    def test_get_user_by_phone(self, test_db):
        """Test retrieving user by phone number."""
        # Create a test user
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        retrieved_user = service.get_by_phone(phone_number="9876543210")
        
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.phone_number == "9876543210"

    def test_update_user(self, test_db):
        """Test updating user profile."""
        # Create a test user
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        
        update_data = UserUpdate(
            district="KL-EKM",
        )
        
        updated_user = service.update(user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.id == user.id
        assert updated_user.district == "KL-EKM"
        assert updated_user.phone_number == "9876543210"  # Unchanged

    def test_update_user_partial(self, test_db):
        """Test partial update - only specified fields are updated."""
        # Create a test user
        user = create_test_user(
            test_db,
            phone_number="9876543210",
            district="KL-TVM",
        )
        
        service = UserService(test_db)
        
        # Only update district
        update_data = UserUpdate(district="KL-PKD")
        updated_user = service.update(user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.district == "KL-PKD"
        assert updated_user.role == "farmer"  # Unchanged

    def test_soft_delete_user(self, test_db):
        """Test user soft deletion (sets deleted_at)."""
        from app.models import User

        # Create a test user
        user = create_test_user(test_db, phone_number="9876543210")
        user_id = user.id

        service = UserService(test_db)

        # Soft delete the user
        result = service.soft_delete(user.id)

        assert result is True

        # Verify user has deleted_at set (query directly to include deleted users)
        deleted_user = test_db.query(User).filter(User.id == user_id).first()
        assert deleted_user is not None
        assert deleted_user.deleted_at is not None

        # get_by_id should return None for soft-deleted users
        assert service.get_by_id(user_id) is None

    def test_get_nonexistent_user(self, test_db):
        """Test getting user that doesn't exist returns None."""
        service = UserService(test_db)
        
        random_id = uuid4()
        user = service.get_by_id(random_id)
        
        assert user is None

    def test_get_nonexistent_user_by_phone(self, test_db):
        """Test getting user by non-existent phone returns None."""
        service = UserService(test_db)
        
        user = service.get_by_phone(phone_number="0000000000")
        
        assert user is None

    def test_list_users(self, test_db):
        """Test listing users with pagination."""
        # Create multiple test users
        create_test_user(test_db, phone_number="9876543210")
        create_test_user(test_db, phone_number="9876543211")
        create_test_user(test_db, phone_number="9876543212")
        
        service = UserService(test_db)
        
        users = service.get_all(skip=0, limit=10)
        
        assert len(users) == 3

    def test_list_users_pagination(self, test_db):
        """Test listing users with pagination limits."""
        # Create multiple test users
        create_test_user(test_db, phone_number="9876543210")
        create_test_user(test_db, phone_number="9876543211")
        create_test_user(test_db, phone_number="9876543212")
        
        service = UserService(test_db)
        
        # Get only first 2
        users = service.get_all(skip=0, limit=2)
        assert len(users) == 2
        
        # Get remaining
        users = service.get_all(skip=2, limit=10)
        assert len(users) == 1

    def test_count_users(self, test_db):
        """Test counting total users."""
        # Create multiple test users
        create_test_user(test_db, phone_number="9876543210")
        create_test_user(test_db, phone_number="9876543211")
        
        service = UserService(test_db)
        
        count = service.count()
        
        assert count == 2

    def test_update_nonexistent_user(self, test_db):
        """Test updating non-existent user returns None."""
        service = UserService(test_db)
        
        update_data = UserUpdate(district="KL-PKD")
        result = service.update(uuid4(), update_data)
        
        assert result is None

    def test_soft_delete_nonexistent_user(self, test_db):
        """Test soft deleting non-existent user returns False."""
        service = UserService(test_db)
        
        result = service.soft_delete(uuid4())
        
        assert result is False

    def test_create_user_with_different_roles(self, test_db):
        """Test creating users with different valid roles."""
        service = UserService(test_db)
        
        # Create farmer
        farmer = service.create(
            phone_number="9876543210",
            role="farmer",
            district="KL-TVM",
        )
        assert farmer.role == "farmer"
        
        # Create admin
        admin = service.create(
            phone_number="9876543211",
            role="admin",
            district="KL-TVM",
        )
        assert admin.role == "admin"

    def test_get_users_by_role(self, test_db):
        """Test filtering users by role."""
        # Create users with different roles
        create_test_user(test_db, phone_number="9876543210", role="farmer")
        create_test_user(test_db, phone_number="9876543211", role="farmer")
        create_test_user(test_db, phone_number="9876543212", role="admin")
        
        service = UserService(test_db)
        
        farmers = service.get_all(role="farmer")
        admins = service.get_all(role="admin")
        
        assert len(farmers) == 2
        assert len(admins) == 1

    # ============ EDGE CASE TESTS ============

    def test_create_user_invalid_phone_empty(self, test_db):
        """Test creating user with empty phone number raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Phone number is required"):
            service.create(phone_number="", role="farmer")

    def test_create_user_invalid_phone_short(self, test_db):
        """Test creating user with short phone number raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Phone number must be 10 digits"):
            service.create(phone_number="12345", role="farmer")

    def test_create_user_invalid_phone_start(self, test_db):
        """Test creating user with phone not starting with 6-9 raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Phone number must start with"):
            service.create(phone_number="1234567890", role="farmer")

    def test_create_user_invalid_phone_non_digit(self, test_db):
        """Test creating user with non-digit phone raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Phone number must contain only digits"):
            service.create(phone_number="98765abc10", role="farmer")

    def test_create_user_invalid_role(self, test_db):
        """Test creating user with invalid role raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Role must be one of"):
            service.create(phone_number="9876543210", role="superuser")

    def test_create_user_invalid_district(self, test_db):
        """Test creating user with invalid district raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="District must be one of"):
            service.create(phone_number="9876543210", role="farmer", district="INVALID-DISTRICT")

    def test_create_user_invalid_language(self, test_db):
        """Test creating user with invalid language raises error."""
        service = UserService(test_db)
        
        with pytest.raises(ValueError, match="Language must be"):
            service.create(phone_number="9876543210", role="farmer", language="fr")

    def test_get_all_users_invalid_role_returns_empty(self, test_db):
        """Test get_all with invalid role returns empty list."""
        create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        
        users = service.get_all(role="invalid_role")
        
        assert len(users) == 0

    def test_get_all_users_invalid_district_returns_empty(self, test_db):
        """Test get_all with invalid district returns empty list."""
        create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        
        users = service.get_all(district="INVALID-DISTRICT")
        
        assert len(users) == 0

    def test_count_users_invalid_role_returns_zero(self, test_db):
        """Test count with invalid role returns 0."""
        create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        
        count = service.count(role="invalid_role")
        
        assert count == 0

    def test_count_users_invalid_district_returns_zero(self, test_db):
        """Test count with invalid district returns 0."""
        create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        
        count = service.count(district="INVALID-DISTRICT")
        
        assert count == 0

    def test_count_users_by_district(self, test_db):
        """Test counting users by district."""
        create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        create_test_user(test_db, phone_number="9876543211", district="KL-TVM")
        create_test_user(test_db, phone_number="9876543212", district="KL-EKM")
        
        service = UserService(test_db)
        
        tvm_count = service.count(district="KL-TVM")
        ekm_count = service.count(district="KL-EKM")
        
        assert tvm_count == 2
        assert ekm_count == 1

    def test_count_users_by_role(self, test_db):
        """Test counting users by role."""
        create_test_user(test_db, phone_number="9876543210", role="farmer")
        create_test_user(test_db, phone_number="9876543211", role="farmer")
        create_test_user(test_db, phone_number="9876543212", role="admin")
        
        service = UserService(test_db)
        
        farmer_count = service.count(role="farmer")
        admin_count = service.count(role="admin")
        
        assert farmer_count == 2
        assert admin_count == 1

    def test_restore_soft_deleted_user(self, test_db):
        """Test restoring a soft-deleted user."""
        # Create and soft delete a user
        user = create_test_user(test_db, phone_number="9876543210")
        user_id = user.id
        
        service = UserService(test_db)
        service.soft_delete(user_id)
        
        # Verify user is deleted
        assert service.get_by_id(user_id) is None
        
        # Restore the user
        restored = service.restore(user_id)
        
        assert restored is not None
        assert restored.id == user_id
        assert restored.deleted_at is None

    def test_restore_nonexistent_user(self, test_db):
        """Test restoring a non-existent user returns None."""
        service = UserService(test_db)
        
        result = service.restore(uuid4())
        
        assert result is None

    def test_restore_active_user_returns_none(self, test_db):
        """Test restoring an active (non-deleted) user returns None."""
        user = create_test_user(test_db, phone_number="9876543210")
        
        service = UserService(test_db)
        
        result = service.restore(user.id)
        
        assert result is None

    def test_is_profile_complete_with_district(self, test_db):
        """Test is_profile_complete returns True when district is set."""
        user = create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        
        service = UserService(test_db)
        
        assert service.is_profile_complete(user) is True

    def test_is_profile_complete_without_district(self, test_db):
        """Test is_profile_complete returns False when district is None."""
        service = UserService(test_db)
        
        user = service.create(phone_number="9876543210", role="farmer", district=None)
        
        assert service.is_profile_complete(user) is False

    def test_get_by_district(self, test_db):
        """Test getting users by district."""
        create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        create_test_user(test_db, phone_number="9876543211", district="KL-TVM")
        create_test_user(test_db, phone_number="9876543212", district="KL-EKM")
        
        service = UserService(test_db)
        
        tvm_users = service.get_by_district("KL-TVM")
        ekm_users = service.get_by_district("KL-EKM")
        
        assert len(tvm_users) == 2
        assert len(ekm_users) == 1

    def test_get_by_invalid_district_returns_empty(self, test_db):
        """Test getting users by invalid district returns empty list."""
        create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        
        service = UserService(test_db)
        
        users = service.get_by_district("INVALID-DISTRICT")
        
        assert len(users) == 0

    def test_update_user_with_empty_data(self, test_db):
        """Test updating user with no fields returns original user."""
        user = create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        
        service = UserService(test_db)
        
        update_data = UserUpdate()  # Empty update
        result = service.update(user.id, update_data)
        
        assert result is not None
        assert result.id == user.id
        assert result.district == "KL-TVM"

    def test_update_user_direct(self, test_db):
        """Test updating user object directly with update_user method."""
        user = create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        
        service = UserService(test_db)
        
        update_data = UserUpdate(district="KL-EKM")
        result = service.update_user(user, update_data)
        
        assert result is not None
        assert result.district == "KL-EKM"

    def test_update_user_direct_empty_data(self, test_db):
        """Test update_user with empty data returns unchanged user."""
        user = create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        
        service = UserService(test_db)
        
        update_data = UserUpdate()  # Empty update
        result = service.update_user(user, update_data)
        
        assert result is not None
        assert result.district == "KL-TVM"