import pytest
from uuid import uuid4

from tests.utils import create_test_commodity
from app.commodities.service import CommodityService
from app.commodities.schemas import CommodityCreate, CommodityUpdate


class TestCommodityService:
    """Tests for Commodity CRUD operations."""

    def test_create_commodity(self, test_db):
        """Test commodity creation with valid data."""
        service = CommodityService(test_db)
        
        commodity_data = CommodityCreate(
            name="Rice",
            category="Grains",
            unit="quintal",
        )
        
        commodity = service.create(commodity_data)
        
        assert commodity is not None
        assert commodity.id is not None
        assert commodity.name == "Rice"
        assert commodity.category == "Grains"
        assert commodity.unit == "quintal"
        assert commodity.created_at is not None

    def test_create_commodity_duplicate_name(self, test_db):
        """Test that creating commodity with duplicate name raises error."""
        service = CommodityService(test_db)
        
        # Create first commodity
        commodity_data = CommodityCreate(
            name="Rice",
            category="Grains",
            unit="quintal",
        )
        service.create(commodity_data)
        
        # Try to create second commodity with same name
        duplicate_data = CommodityCreate(
            name="Rice",
            category="Grains",
            unit="kg",
        )
        
        with pytest.raises(Exception):
            service.create(duplicate_data)

    def test_get_commodity_by_id(self, test_db):
        """Test retrieving commodity by ID."""
        # Create a test commodity
        commodity = create_test_commodity(test_db, name="Wheat")
        
        service = CommodityService(test_db)
        retrieved = service.get_by_id(commodity.id)
        
        assert retrieved is not None
        assert retrieved.id == commodity.id
        assert retrieved.name == "Wheat"

    def test_get_commodities_list(self, test_db):
        """Test listing commodities with pagination."""
        # Create multiple test commodities
        create_test_commodity(test_db, name="Rice", category="Grains")
        create_test_commodity(test_db, name="Wheat", category="Grains")
        create_test_commodity(test_db, name="Tomato", category="Vegetables")
        
        service = CommodityService(test_db)
        
        commodities = service.get_all(skip=0, limit=10)
        
        assert len(commodities) == 3

    def test_get_commodities_pagination(self, test_db):
        """Test listing commodities with pagination limits."""
        # Create multiple test commodities
        create_test_commodity(test_db, name="Rice", category="Grains")
        create_test_commodity(test_db, name="Wheat", category="Grains")
        create_test_commodity(test_db, name="Tomato", category="Vegetables")
        
        service = CommodityService(test_db)
        
        # Get only first 2
        commodities = service.get_all(skip=0, limit=2)
        assert len(commodities) == 2
        
        # Get remaining
        commodities = service.get_all(skip=2, limit=10)
        assert len(commodities) == 1

    def test_filter_commodities_by_category(self, test_db):
        """Test filtering commodities by category."""
        # Create commodities with different categories
        create_test_commodity(test_db, name="Rice", category="Grains")
        create_test_commodity(test_db, name="Wheat", category="Grains")
        create_test_commodity(test_db, name="Tomato", category="Vegetables")
        create_test_commodity(test_db, name="Onion", category="Vegetables")
        create_test_commodity(test_db, name="Apple", category="Fruits")
        
        service = CommodityService(test_db)
        
        grains = service.get_all(category="Grains")
        vegetables = service.get_all(category="Vegetables")
        fruits = service.get_all(category="Fruits")
        
        assert len(grains) == 2
        assert len(vegetables) == 2
        assert len(fruits) == 1

    def test_update_commodity(self, test_db):
        """Test updating commodity details."""
        # Create a test commodity
        commodity = create_test_commodity(
            test_db,
            name="Rice",
            category="Grains",
            unit="quintal",
        )
        
        service = CommodityService(test_db)
        
        update_data = CommodityUpdate(
            name="Basmati Rice",
            category="Premium Grains",
        )
        
        updated = service.update(commodity.id, update_data)
        
        assert updated is not None
        assert updated.id == commodity.id
        assert updated.name == "Basmati Rice"
        assert updated.category == "Premium Grains"
        assert updated.unit == "quintal"  # Unchanged

    def test_update_commodity_partial(self, test_db):
        """Test partial update - only specified fields are updated."""
        # Create a test commodity
        commodity = create_test_commodity(
            test_db,
            name="Rice",
            category="Grains",
            unit="quintal",
        )
        
        service = CommodityService(test_db)
        
        # Only update name
        update_data = CommodityUpdate(name="Brown Rice")
        updated = service.update(commodity.id, update_data)
        
        assert updated is not None
        assert updated.name == "Brown Rice"
        assert updated.category == "Grains"  # Unchanged
        assert updated.unit == "quintal"  # Unchanged

    def test_delete_commodity(self, test_db):
        """Test commodity soft deletion (sets is_active=False)."""
        # Create a test commodity
        commodity = create_test_commodity(test_db, name="Rice")
        
        service = CommodityService(test_db)
        
        # Delete the commodity
        result = service.delete(commodity.id)
        
        assert result is True
        
        # Verify commodity is deactivated
        deleted = service.get_by_id(commodity.id)
        assert deleted is None or deleted.is_active is False

    def test_get_nonexistent_commodity(self, test_db):
        """Test getting commodity that doesn't exist returns None."""
        service = CommodityService(test_db)
        
        random_id = uuid4()
        commodity = service.get_by_id(random_id)
        
        assert commodity is None

    def test_update_nonexistent_commodity(self, test_db):
        """Test updating non-existent commodity returns None."""
        service = CommodityService(test_db)
        
        update_data = CommodityUpdate(name="New Name")
        result = service.update(uuid4(), update_data)
        
        assert result is None

    def test_delete_nonexistent_commodity(self, test_db):
        """Test deleting non-existent commodity returns False."""
        service = CommodityService(test_db)
        
        result = service.delete(uuid4())
        
        assert result is False

    def test_count_commodities(self, test_db):
        """Test counting total commodities."""
        # Create multiple test commodities
        create_test_commodity(test_db, name="Rice")
        create_test_commodity(test_db, name="Wheat")
        create_test_commodity(test_db, name="Tomato")
        
        service = CommodityService(test_db)
        
        count = service.count()
        
        assert count == 3

    def test_count_commodities_by_category(self, test_db):
        """Test counting commodities by category."""
        # Create commodities with different categories
        create_test_commodity(test_db, name="Rice", category="Grains")
        create_test_commodity(test_db, name="Wheat", category="Grains")
        create_test_commodity(test_db, name="Tomato", category="Vegetables")
        
        service = CommodityService(test_db)
        
        grains_count = service.count(category="Grains")
        vegetables_count = service.count(category="Vegetables")
        
        assert grains_count == 2
        assert vegetables_count == 1

    # ============ EDGE CASE TESTS ============

    def test_search_commodities(self, test_db):
        """Test searching commodities by name."""
        create_test_commodity(test_db, name="Basmati Rice", category="Grains")
        create_test_commodity(test_db, name="Brown Rice", category="Grains")
        create_test_commodity(test_db, name="Wheat", category="Grains")
        create_test_commodity(test_db, name="Tomato", category="Vegetables")
        
        service = CommodityService(test_db)
        
        # Search for "Rice" should return both rice commodities
        results = service.search("Rice")
        
        assert len(results) == 2
        names = [c.name for c in results]
        assert "Basmati Rice" in names
        assert "Brown Rice" in names

    def test_search_commodities_case_insensitive(self, test_db):
        """Test searching commodities is case insensitive."""
        create_test_commodity(test_db, name="Basmati Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        # Search with different cases
        results_lower = service.search("rice")
        results_upper = service.search("RICE")
        
        assert len(results_lower) == 1
        assert len(results_upper) == 1

    def test_search_commodities_no_match(self, test_db):
        """Test searching commodities with no matches."""
        create_test_commodity(test_db, name="Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        results = service.search("NonExistent")
        
        assert len(results) == 0

    def test_search_commodities_with_limit(self, test_db):
        """Test searching commodities respects limit."""
        create_test_commodity(test_db, name="Rice 1", category="Grains")
        create_test_commodity(test_db, name="Rice 2", category="Grains")
        create_test_commodity(test_db, name="Rice 3", category="Grains")
        create_test_commodity(test_db, name="Rice 4", category="Grains")
        
        service = CommodityService(test_db)
        
        results = service.search("Rice", limit=2)
        
        assert len(results) == 2

    def test_get_commodity_by_name(self, test_db):
        """Test getting commodity by name."""
        commodity = create_test_commodity(test_db, name="Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        result = service.get_by_name("Rice")
        
        assert result is not None
        assert result.id == commodity.id
        assert result.name == "Rice"

    def test_get_commodity_by_name_not_found(self, test_db):
        """Test getting commodity by name that doesn't exist."""
        create_test_commodity(test_db, name="Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        result = service.get_by_name("NonExistent")
        
        assert result is None

    def test_create_duplicate_commodity_raises_valueerror(self, test_db):
        """Test creating duplicate commodity raises ValueError with message."""
        service = CommodityService(test_db)
        
        # Create first commodity
        commodity_data = CommodityCreate(name="Rice", category="Grains")
        service.create(commodity_data)
        
        # Try to create duplicate
        duplicate_data = CommodityCreate(name="Rice", category="Premium")
        
        with pytest.raises(ValueError, match="already exists"):
            service.create(duplicate_data)

    def test_update_commodity_duplicate_name_raises_valueerror(self, test_db):
        """Test updating commodity to duplicate name raises ValueError."""
        service = CommodityService(test_db)
        
        # Create two commodities
        rice_data = CommodityCreate(name="Rice", category="Grains")
        wheat_data = CommodityCreate(name="Wheat", category="Grains")
        
        rice = service.create(rice_data)
        wheat = service.create(wheat_data)
        
        # Try to update wheat's name to "Rice"
        update_data = CommodityUpdate(name="Rice")
        
        with pytest.raises(ValueError, match="already exists"):
            service.update(wheat.id, update_data)

    def test_update_commodity_same_name_allowed(self, test_db):
        """Test updating commodity with same name is allowed."""
        service = CommodityService(test_db)
        
        # Create commodity
        commodity_data = CommodityCreate(name="Rice", category="Grains")
        commodity = service.create(commodity_data)
        
        # Update with same name but different category
        update_data = CommodityUpdate(name="Rice", category="Premium Grains")
        result = service.update(commodity.id, update_data)
        
        assert result is not None
        assert result.name == "Rice"
        assert result.category == "Premium Grains"

    def test_update_commodity_empty_data(self, test_db):
        """Test updating commodity with no fields returns original."""
        commodity = create_test_commodity(test_db, name="Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        update_data = CommodityUpdate()  # Empty update
        result = service.update(commodity.id, update_data)
        
        assert result is not None
        assert result.id == commodity.id
        assert result.name == "Rice"
        assert result.category == "Grains"

    def test_get_all_empty_database(self, test_db):
        """Test get_all on empty database returns empty list."""
        service = CommodityService(test_db)
        
        results = service.get_all()
        
        assert len(results) == 0

    def test_count_empty_database(self, test_db):
        """Test count on empty database returns 0."""
        service = CommodityService(test_db)
        
        count = service.count()
        
        assert count == 0

    def test_count_with_nonexistent_category(self, test_db):
        """Test count with non-existent category returns 0."""
        create_test_commodity(test_db, name="Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        count = service.count(category="NonExistent")
        
        assert count == 0

    def test_get_all_with_nonexistent_category(self, test_db):
        """Test get_all with non-existent category returns empty list."""
        create_test_commodity(test_db, name="Rice", category="Grains")
        
        service = CommodityService(test_db)
        
        results = service.get_all(category="NonExistent")
        
        assert len(results) == 0

    def test_create_commodity_with_local_name(self, test_db):
        """Test creating commodity with local name."""
        service = CommodityService(test_db)
        
        commodity_data = CommodityCreate(
            name="Rice",
            name_local="अरी",
            category="Grains",
            unit="quintal",
        )
        
        commodity = service.create(commodity_data)
        
        assert commodity is not None
        assert commodity.name == "Rice"
        assert commodity.name_local == "अरी"

    def test_pagination_skip_all(self, test_db):
        """Test pagination when skip exceeds total count."""
        create_test_commodity(test_db, name="Rice")
        create_test_commodity(test_db, name="Wheat")
        
        service = CommodityService(test_db)
        
        results = service.get_all(skip=100, limit=10)
        
        assert len(results) == 0