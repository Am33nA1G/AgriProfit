import pytest
from uuid import uuid4

from tests.utils import create_test_mandi
from app.mandi.service import MandiService
from app.mandi.schemas import MandiCreate, MandiUpdate


class TestMandiService:
    """Tests for Mandi CRUD operations."""

    def test_create_mandi(self, test_db):
        """Test mandi creation with valid data."""
        service = MandiService(test_db)
        
        mandi_data = MandiCreate(
            name="Delhi Mandi",
            district="Central Delhi",
            state="Delhi",
            market_code="MKT-DELHI-001",
        )
        
        mandi = service.create(mandi_data)
        
        assert mandi is not None
        assert mandi.id is not None
        assert mandi.name == "Delhi Mandi"
        assert mandi.district == "Central Delhi"
        assert mandi.state == "Delhi"
        assert mandi.market_code == "MKT-DELHI-001"
        assert mandi.is_active is True
        assert mandi.created_at is not None

    def test_create_mandi_duplicate_market_code(self, test_db):
        """Test that creating mandi with duplicate market_code raises error."""
        service = MandiService(test_db)
        
        # Create first mandi
        mandi_data = MandiCreate(
            name="Delhi Mandi",
            district="Central Delhi",
            state="Delhi",
            market_code="MKT-DELHI-001",
        )
        service.create(mandi_data)
        
        # Try to create second mandi with same market_code
        duplicate_data = MandiCreate(
            name="Another Mandi",
            district="South Delhi",
            state="Delhi",
            market_code="MKT-DELHI-001",
        )
        
        with pytest.raises(Exception):
            service.create(duplicate_data)

    def test_get_mandi_by_id(self, test_db):
        """Test retrieving mandi by ID."""
        # Create a test mandi
        mandi = create_test_mandi(test_db, name="Test Mandi")
        
        service = MandiService(test_db)
        retrieved = service.get_by_id(mandi.id)
        
        assert retrieved is not None
        assert retrieved.id == mandi.id
        assert retrieved.name == "Test Mandi"

    def test_get_mandi_by_market_code(self, test_db):
        """Test retrieving mandi by market code."""
        # Create a test mandi
        mandi = create_test_mandi(
            test_db,
            name="Test Mandi",
            market_code="MKT-TEST-001",
        )
        
        service = MandiService(test_db)
        retrieved = service.get_by_market_code("MKT-TEST-001")
        
        assert retrieved is not None
        assert retrieved.id == mandi.id
        assert retrieved.market_code == "MKT-TEST-001"

    def test_get_mandis_list(self, test_db):
        """Test listing mandis with pagination."""
        # Create multiple test mandis
        create_test_mandi(test_db, name="Mandi 1")
        create_test_mandi(test_db, name="Mandi 2")
        create_test_mandi(test_db, name="Mandi 3")
        
        service = MandiService(test_db)
        
        mandis = service.get_all(skip=0, limit=10)
        
        assert len(mandis) == 3

    def test_get_mandis_pagination(self, test_db):
        """Test listing mandis with pagination limits."""
        # Create multiple test mandis
        create_test_mandi(test_db, name="Mandi 1")
        create_test_mandi(test_db, name="Mandi 2")
        create_test_mandi(test_db, name="Mandi 3")
        
        service = MandiService(test_db)
        
        # Get only first 2
        mandis = service.get_all(skip=0, limit=2)
        assert len(mandis) == 2
        
        # Get remaining
        mandis = service.get_all(skip=2, limit=10)
        assert len(mandis) == 1

    def test_filter_mandis_by_state(self, test_db):
        """Test filtering mandis by state."""
        # Create mandis in different states
        create_test_mandi(test_db, name="Mandi 1", state="Delhi")
        create_test_mandi(test_db, name="Mandi 2", state="Delhi")
        create_test_mandi(test_db, name="Mandi 3", state="Maharashtra")
        create_test_mandi(test_db, name="Mandi 4", state="Punjab")
        
        service = MandiService(test_db)
        
        delhi_mandis = service.get_all(state="Delhi")
        maharashtra_mandis = service.get_all(state="Maharashtra")
        punjab_mandis = service.get_all(state="Punjab")
        
        assert len(delhi_mandis) == 2
        assert len(maharashtra_mandis) == 1
        assert len(punjab_mandis) == 1

    def test_filter_mandis_by_district(self, test_db):
        """Test filtering mandis by district."""
        # Create mandis in different districts
        create_test_mandi(test_db, name="Mandi 1", district="Central Delhi", state="Delhi")
        create_test_mandi(test_db, name="Mandi 2", district="Central Delhi", state="Delhi")
        create_test_mandi(test_db, name="Mandi 3", district="South Delhi", state="Delhi")
        create_test_mandi(test_db, name="Mandi 4", district="Pune", state="Maharashtra")
        
        service = MandiService(test_db)
        
        central_delhi = service.get_all(district="Central Delhi")
        south_delhi = service.get_all(district="South Delhi")
        pune = service.get_all(district="Pune")
        
        assert len(central_delhi) == 2
        assert len(south_delhi) == 1
        assert len(pune) == 1

    def test_filter_mandis_by_state_and_district(self, test_db):
        """Test filtering mandis by both state and district."""
        # Create mandis
        create_test_mandi(test_db, name="Mandi 1", district="Central", state="Delhi")
        create_test_mandi(test_db, name="Mandi 2", district="South", state="Delhi")
        create_test_mandi(test_db, name="Mandi 3", district="Central", state="Maharashtra")
        
        service = MandiService(test_db)
        
        # Filter by both
        results = service.get_all(state="Delhi", district="Central")
        
        assert len(results) == 1
        assert results[0].name == "Mandi 1"

    def test_update_mandi(self, test_db):
        """Test updating mandi details."""
        # Create a test mandi
        mandi = create_test_mandi(
            test_db,
            name="Old Mandi",
            district="Old District",
            state="Old State",
        )
        
        service = MandiService(test_db)
        
        update_data = MandiUpdate(
            name="New Mandi",
            district="New District",
        )
        
        updated = service.update(mandi.id, update_data)
        
        assert updated is not None
        assert updated.id == mandi.id
        assert updated.name == "New Mandi"
        assert updated.district == "New District"
        assert updated.state == "Old State"  # Unchanged

    def test_update_mandi_partial(self, test_db):
        """Test partial update - only specified fields are updated."""
        # Create a test mandi
        mandi = create_test_mandi(
            test_db,
            name="Original Mandi",
            district="Original District",
            state="Original State",
        )
        
        service = MandiService(test_db)
        
        # Only update name
        update_data = MandiUpdate(name="Updated Mandi")
        updated = service.update(mandi.id, update_data)
        
        assert updated is not None
        assert updated.name == "Updated Mandi"
        assert updated.district == "Original District"  # Unchanged
        assert updated.state == "Original State"  # Unchanged

    def test_update_mandi_is_active(self, test_db):
        """Test updating mandi is_active status."""
        # Create a test mandi
        mandi = create_test_mandi(test_db, name="Test Mandi")
        
        service = MandiService(test_db)
        
        # Deactivate mandi
        update_data = MandiUpdate(is_active=False)
        updated = service.update(mandi.id, update_data)
        
        assert updated is not None
        assert updated.is_active is False

    def test_delete_mandi(self, test_db):
        """Test mandi soft deletion (sets is_active=False)."""
        # Create a test mandi
        mandi = create_test_mandi(test_db, name="Test Mandi")
        
        service = MandiService(test_db)
        
        # Delete the mandi
        result = service.delete(mandi.id)
        
        assert result is True
        
        # Verify mandi is deactivated
        deleted = service.get_by_id(mandi.id)
        assert deleted is None or deleted.is_active is False

    def test_get_nonexistent_mandi(self, test_db):
        """Test getting mandi that doesn't exist returns None."""
        service = MandiService(test_db)
        
        random_id = uuid4()
        mandi = service.get_by_id(random_id)
        
        assert mandi is None

    def test_get_nonexistent_mandi_by_market_code(self, test_db):
        """Test getting mandi by non-existent market code returns None."""
        service = MandiService(test_db)
        
        mandi = service.get_by_market_code("NON-EXISTENT-CODE")
        
        assert mandi is None

    def test_update_nonexistent_mandi(self, test_db):
        """Test updating non-existent mandi returns None."""
        service = MandiService(test_db)
        
        update_data = MandiUpdate(name="New Name")
        result = service.update(uuid4(), update_data)
        
        assert result is None

    def test_delete_nonexistent_mandi(self, test_db):
        """Test deleting non-existent mandi returns False."""
        service = MandiService(test_db)
        
        result = service.delete(uuid4())
        
        assert result is False

    def test_count_mandis(self, test_db):
        """Test counting total mandis."""
        # Create multiple test mandis
        create_test_mandi(test_db, name="Mandi 1")
        create_test_mandi(test_db, name="Mandi 2")
        create_test_mandi(test_db, name="Mandi 3")
        
        service = MandiService(test_db)
        
        count = service.count()
        
        assert count == 3

    def test_count_mandis_by_state(self, test_db):
        """Test counting mandis by state."""
        # Create mandis in different states
        create_test_mandi(test_db, name="Mandi 1", state="Delhi")
        create_test_mandi(test_db, name="Mandi 2", state="Delhi")
        create_test_mandi(test_db, name="Mandi 3", state="Maharashtra")
        
        service = MandiService(test_db)
        
        delhi_count = service.count(state="Delhi")
        maharashtra_count = service.count(state="Maharashtra")
        
        assert delhi_count == 2
        assert maharashtra_count == 1

    def test_get_active_mandis_only(self, test_db):
        """Test that get_all returns only active mandis by default."""
        # Create active and inactive mandis
        create_test_mandi(test_db, name="Active Mandi 1")
        create_test_mandi(test_db, name="Active Mandi 2")
        inactive_mandi = create_test_mandi(test_db, name="Inactive Mandi")
        
        service = MandiService(test_db)
        
        # Deactivate one mandi
        service.update(inactive_mandi.id, MandiUpdate(is_active=False))
        
        # Get all should return only active
        active_mandis = service.get_all(is_active=True)
        
        assert len(active_mandis) == 2
        names = [m.name for m in active_mandis]
        assert "Active Mandi 1" in names
        assert "Active Mandi 2" in names
        assert "Inactive Mandi" not in names

    # ============ EDGE CASE TESTS ============

    def test_search_mandis(self, test_db):
        """Test searching mandis by name."""
        create_test_mandi(test_db, name="Delhi Mandi")
        create_test_mandi(test_db, name="Mumbai Mandi")
        create_test_mandi(test_db, name="Chennai Mandi")
        
        service = MandiService(test_db)
        
        # Search for "Mandi" should return all
        results = service.search("Mandi")
        assert len(results) == 3
        
        # Search for "Delhi" should return 1
        results = service.search("Delhi")
        assert len(results) == 1
        assert results[0].name == "Delhi Mandi"

    def test_search_mandis_by_code(self, test_db):
        """Test searching mandis by market code."""
        create_test_mandi(test_db, name="Mandi 1", market_code="CODE-123")
        create_test_mandi(test_db, name="Mandi 2", market_code="OTHER-456")
        
        service = MandiService(test_db)
        
        results = service.search("CODE")
        assert len(results) == 1
        assert results[0].market_code == "CODE-123"

    def test_restore_mandi(self, test_db):
        """Test restoring a soft-deleted mandi."""
        mandi = create_test_mandi(test_db, name="Test Mandi")
        service = MandiService(test_db)
        
        # Delete
        service.delete(mandi.id)
        assert service.get_by_id(mandi.id) is None
        
        # Restore
        restored = service.restore(mandi.id)
        assert restored is not None
        assert restored.is_active is True
        assert service.get_by_id(mandi.id) is not None

    def test_restore_nonexistent_mandi(self, test_db):
        """Test restoring non-existent mandi returns None."""
        service = MandiService(test_db)
        result = service.restore(uuid4())
        assert result is None

    def test_update_mandi_empty_data(self, test_db):
        """Test updating mandi with no fields."""
        mandi = create_test_mandi(test_db)
        service = MandiService(test_db)
        
        update_data = MandiUpdate()
        result = service.update(mandi.id, update_data)
        
        assert result is not None
        assert result.id == mandi.id

    def test_update_mandi_duplicate_code(self, test_db):
        """Test updating mandi with duplicate market code raises error."""
        mandi1 = create_test_mandi(test_db, name="Mandi 1", market_code="CODE-1")
        mandi2 = create_test_mandi(test_db, name="Mandi 2", market_code="CODE-2")
        
        service = MandiService(test_db)
        
        update_data = MandiUpdate(market_code="CODE-1")
        
        with pytest.raises(ValueError, match="already exists"):
            service.update(mandi2.id, update_data)

    def test_get_by_district(self, test_db):
        """Test get_by_district."""
        create_test_mandi(test_db, district="District A")
        create_test_mandi(test_db, district="District A")
        create_test_mandi(test_db, district="District B")
        
        service = MandiService(test_db)
        
        results = service.get_by_district("District A")
        assert len(results) == 2