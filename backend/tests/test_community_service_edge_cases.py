import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from app.community.service import CommunityPostService
from app.community.schemas import CommunityPostCreate, CommunityPostUpdate
from tests.utils import create_test_user


class TestCommunityServiceEdgeCases:
    """Edge case tests for CommunityPostService."""

    def test_update_post_not_found(self, test_db):
        """Test updating a non-existent post returns None."""
        service = CommunityPostService(test_db)
        update_data = CommunityPostUpdate(title="New Title")
        
        result = service.update(uuid4(), update_data)
        
        assert result is None

    def test_update_post_by_non_author(self, test_db):
        """Test updating post by user who is not the author (if service enforces it)."""
        # Create author and another user
        author = create_test_user(test_db, phone_number="9876543210")
        other_user = create_test_user(test_db, phone_number="9876543211")
        
        service = CommunityPostService(test_db)
        
        # Create post
        post = service.create(
            CommunityPostCreate(title="Title", content="This is valid test content for community post", post_type="discussion"),
            user_id=author.id
        )
        
        # Try to update as other user
        update_data = CommunityPostUpdate(title="New Title")
        # The service update method optionally takes user_id to enforce authorship
        result = service.update(post.id, update_data, user_id=other_user.id)
        
        # If user_id is passed and doesn't match, the filter returns None, so result should be None
        assert result is None

    def test_delete_post_not_found(self, test_db):
        """Test deleting a non-existent post returns False."""
        service = CommunityPostService(test_db)
        
        result = service.delete(uuid4())
        
        assert result is False

    def test_delete_post_by_non_author(self, test_db):
        """Test deleting post by user who is not the author."""
        author = create_test_user(test_db, phone_number="9876543210")
        other_user = create_test_user(test_db, phone_number="9876543211")
        
        service = CommunityPostService(test_db)
        
        post = service.create(
            CommunityPostCreate(title="Title", content="This is valid test content for community post", post_type="discussion"),
            user_id=author.id
        )

        # Try to delete as other user
        result = service.delete(post.id, user_id=other_user.id)
        
        assert result is False
        # Verify post still exists
        assert service.get_by_id(post.id) is not None

    def test_get_posts_empty_result(self, test_db):
        """Test filtering that returns no posts."""
        create_test_user(test_db, phone_number="9876543210")
        
        service = CommunityPostService(test_db)
        
        # Filter by a district that has no posts
        posts = service.get_all(district="NonExistentDistrict")
        
        assert len(posts) == 0

    def test_get_posts_with_multiple_filters(self, test_db):
        """Test filtering with multiple criteria."""
        user = create_test_user(test_db, phone_number="9876543210", district="KL-TVM")
        
        service = CommunityPostService(test_db)
        
        # Create posts matching various criteria
        service.create(
            CommunityPostCreate(title="Match", content="This is valid test content for community post", post_type="discussion", district="KL-TVM"),
            user_id=user.id
        )
        service.create(
            CommunityPostCreate(title="No Match Type", content="This is valid test content for community post", post_type="question", district="KL-TVM"),
            user_id=user.id
        )
        service.create(
            CommunityPostCreate(title="No Match District", content="This is valid test content for community post", post_type="discussion", district="KL-EKM"),
            user_id=user.id
        )

        # Filter by user + type + district
        results = service.get_all(
            user_id=user.id,
            post_type="discussion",
            district="KL-TVM"
        )
        
        assert len(results) == 1
        assert results[0].title == "Match"

    def test_create_post_with_invalid_type_error(self, test_db):
        """Test creating post with invalid type (if DB constraint enforces it)."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = CommunityPostService(test_db)
        
        # The schema validation might pass if we use the model directly or if validation is bypassed,
        # but the DB constraint should fail.
        # However, typically Pydantic catches this first. 
        # Here we test if the service handles DB errors or passes them through.
        
        # If we try to bypass pydantic validation or if pydantic allows it but DB doesn't:
        with pytest.raises(Exception):
            # Pydantic validation should raise ValidationError for invalid post_type
            service.create(
                CommunityPostCreate(title="Title", content="This is valid test content", post_type="invalid_type"),
                user_id=user.id
            )

    def test_search_posts(self, test_db):
        """Test searching posts."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = CommunityPostService(test_db)
        
        service.create(
            CommunityPostCreate(title="Farming Tips", content="Use organic fertilizer for better crops", post_type="discussion"),
            user_id=user.id
        )
        service.create(
            CommunityPostCreate(title="Market News", content="Prices are up this season", post_type="discussion"),
            user_id=user.id
        )
        
        # Search by title
        results = service.search("Farming")
        assert len(results) == 1
        assert results[0].title == "Farming Tips"
        
        # Search by content
        results = service.search("organic")
        assert len(results) == 1
        assert results[0].title == "Farming Tips"

    def test_search_posts_no_match(self, test_db):
        """Test search with no matches."""
        service = CommunityPostService(test_db)
        results = service.search("NonExistent")
        assert len(results) == 0

    def test_update_post_empty_data(self, test_db):
        """Test updating post with empty data."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = CommunityPostService(test_db)
        
        post = service.create(
            CommunityPostCreate(title="Title", content="This is valid test content for community post", post_type="discussion"),
            user_id=user.id
        )

        update_data = CommunityPostUpdate()
        result = service.update(post.id, update_data)
        
        assert result is not None
        assert result.title == "Title"

    def test_restore_post(self, test_db):
        """Test restoring deleted post."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = CommunityPostService(test_db)
        
        post = service.create(
            CommunityPostCreate(title="Title", content="This is valid test content for community post", post_type="discussion"),
            user_id=user.id
        )

        service.delete(post.id)
        assert service.get_by_id(post.id) is None
        
        restored = service.restore(post.id)
        assert restored is not None
        assert restored.id == post.id
        assert service.get_by_id(post.id) is not None

    def test_restore_nonexistent_post(self, test_db):
        """Test restoring non-existent post."""
        service = CommunityPostService(test_db)
        result = service.restore(uuid4())
        assert result is None

    def test_admin_override(self, test_db):
        """Test setting admin override."""
        user = create_test_user(test_db, phone_number="9876543210")
        service = CommunityPostService(test_db)
        
        post = service.create(
            CommunityPostCreate(title="Title", content="This is valid test content for community post", post_type="discussion"),
            user_id=user.id
        )

        result = service.set_admin_override(post.id, True)
        assert result is not None
        assert result.is_admin_override is True

    def test_admin_override_nonexistent(self, test_db):
        """Test setting admin override on non-existent post."""
        service = CommunityPostService(test_db)
        result = service.set_admin_override(uuid4(), True)
        assert result is None

    def test_is_author_check(self, test_db):
        """Test is_author method."""
        author = create_test_user(test_db, phone_number="9876543210")
        other = create_test_user(test_db, phone_number="9876543211")
        service = CommunityPostService(test_db)
        
        post = service.create(
            CommunityPostCreate(title="Title", content="This is valid test content for community post", post_type="discussion"),
            user_id=author.id
        )

        assert service.is_author(post.id, author.id) is True
        assert service.is_author(post.id, other.id) is False
        assert service.is_author(uuid4(), author.id) is False

    def test_get_by_type_invalid(self, test_db):
        """Test get_by_type with invalid type."""
        service = CommunityPostService(test_db)
        results = service.get_by_type("invalid_type")
        assert len(results) == 0

    def test_count_with_invalid_type(self, test_db):
        """Test count with invalid type."""
        service = CommunityPostService(test_db)
        count = service.count(post_type="invalid_type")
        assert count == 0
