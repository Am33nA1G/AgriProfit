import pytest
from uuid import uuid4
from datetime import date, datetime, timedelta

from app.prices.service import PriceHistoryService
from app.prices.schemas import PriceHistoryCreate, PriceHistoryUpdate
from app.models.price_history import PriceHistory
from tests.utils import create_test_commodity, create_test_mandi


class TestPricesServiceEdgeCases:
    """Edge case tests for PriceHistoryService."""

    def test_get_by_id_nonexistent(self, test_db):
        """Test getting non-existent price returns None."""
        service = PriceHistoryService(test_db)
        result = service.get_by_id(uuid4())
        assert result is None

    def test_update_nonexistent(self, test_db):
        """Test updating non-existent price returns None."""
        service = PriceHistoryService(test_db)
        update_data = PriceHistoryUpdate(modal_price=150.00)
        result = service.update(uuid4(), update_data)
        assert result is None

    def test_delete_nonexistent(self, test_db):
        """Test deleting non-existent price returns False."""
        service = PriceHistoryService(test_db)
        result = service.delete(uuid4())
        assert result is False

    def test_get_all_empty_results(self, test_db):
        """Test get_all with filters that match nothing."""
        service = PriceHistoryService(test_db)
        results = service.get_all(commodity_id=uuid4())
        assert len(results) == 0

    def test_get_all_with_date_range_filter(self, test_db):
        """Test get_all with start_date and end_date filters."""
        commodity = create_test_commodity(test_db, name="PriceCommodity1")
        mandi = create_test_mandi(test_db, name="PriceMandi1")
        service = PriceHistoryService(test_db)

        today = date.today()
        # Create prices for different dates
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=10),
            modal_price=100.00,
            min_price=90.00,
            max_price=110.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=5),
            modal_price=110.00,
            min_price=100.00,
            max_price=120.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today,
            modal_price=120.00,
            min_price=110.00,
            max_price=130.00,
        ))

        # Filter by date range (should get middle one only)
        results = service.get_all(
            start_date=today - timedelta(days=7),
            end_date=today - timedelta(days=3),
        )
        assert len(results) == 1
        assert results[0].modal_price == 110.00

    def test_get_latest_when_none_exist(self, test_db):
        """Test get_latest when no prices exist."""
        service = PriceHistoryService(test_db)
        result = service.get_latest(uuid4(), uuid4())
        assert result is None

    def test_get_latest_with_multiple_prices(self, test_db):
        """Test get_latest returns most recent price."""
        commodity = create_test_commodity(test_db, name="PriceCommodity2")
        mandi = create_test_mandi(test_db, name="PriceMandi2")
        service = PriceHistoryService(test_db)

        today = date.today()
        # Create prices for different dates
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=5),
            modal_price=100.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today,
            modal_price=150.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=3),
            modal_price=120.00,
        ))

        result = service.get_latest(commodity.id, mandi.id)
        assert result is not None
        assert result.price_date == today
        assert result.modal_price == 150.00

    def test_combined_filters(self, test_db):
        """Test filtering by commodity_id + mandi_id + date range combined."""
        commodity1 = create_test_commodity(test_db, name="PriceCommodity3")
        commodity2 = create_test_commodity(test_db, name="PriceCommodity4")
        mandi1 = create_test_mandi(test_db, name="PriceMandi3")
        mandi2 = create_test_mandi(test_db, name="PriceMandi4")
        service = PriceHistoryService(test_db)

        today = date.today()
        # Create various prices
        service.create(PriceHistoryCreate(
            commodity_id=commodity1.id,
            mandi_id=mandi1.id,
            price_date=today,
            modal_price=100.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity1.id,
            mandi_id=mandi2.id,
            price_date=today,
            modal_price=110.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity2.id,
            mandi_id=mandi1.id,
            price_date=today,
            modal_price=120.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity1.id,
            mandi_id=mandi1.id,
            price_date=today - timedelta(days=30),
            modal_price=90.00,
        ))

        # Filter by commodity + mandi + date range
        results = service.get_all(
            commodity_id=commodity1.id,
            mandi_id=mandi1.id,
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=1),
        )
        assert len(results) == 1
        assert results[0].modal_price == 100.00

    def test_get_by_commodity_with_date_range(self, test_db):
        """Test get_by_commodity with date range filters."""
        commodity = create_test_commodity(test_db, name="PriceCommodity5")
        mandi = create_test_mandi(test_db, name="PriceMandi5")
        service = PriceHistoryService(test_db)

        today = date.today()
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=15),
            modal_price=100.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=5),
            modal_price=110.00,
        ))

        # Get by commodity with date range
        results = service.get_by_commodity(
            commodity.id,
            start_date=today - timedelta(days=10),
            end_date=today,
        )
        assert len(results) == 1
        assert results[0].modal_price == 110.00

    def test_get_by_mandi_with_date_range(self, test_db):
        """Test get_by_mandi with date range filters."""
        commodity = create_test_commodity(test_db, name="PriceCommodity6")
        mandi = create_test_mandi(test_db, name="PriceMandi6")
        service = PriceHistoryService(test_db)

        today = date.today()
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=15),
            modal_price=100.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=5),
            modal_price=110.00,
        ))

        # Get by mandi with date range
        results = service.get_by_mandi(
            mandi.id,
            start_date=today - timedelta(days=10),
            end_date=today,
        )
        assert len(results) == 1
        assert results[0].modal_price == 110.00

    def test_get_on_date(self, test_db):
        """Test get_on_date returns specific price."""
        commodity = create_test_commodity(test_db, name="PriceCommodity7")
        mandi = create_test_mandi(test_db, name="PriceMandi7")
        service = PriceHistoryService(test_db)

        today = date.today()
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today,
            modal_price=150.00,
        ))

        result = service.get_on_date(commodity.id, mandi.id, today)
        assert result is not None
        assert result.modal_price == 150.00

    def test_get_on_date_not_found(self, test_db):
        """Test get_on_date returns None when not found."""
        service = PriceHistoryService(test_db)
        result = service.get_on_date(uuid4(), uuid4(), date.today())
        assert result is None

    def test_update_with_empty_data(self, test_db):
        """Test update with no changes returns original price."""
        commodity = create_test_commodity(test_db, name="PriceCommodity8")
        mandi = create_test_mandi(test_db, name="PriceMandi8")
        service = PriceHistoryService(test_db)

        price = service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=date.today(),
            modal_price=100.00,
        ))

        update_data = PriceHistoryUpdate()
        result = service.update(price.id, update_data)
        assert result is not None
        assert result.modal_price == 100.00

    def test_update_success(self, test_db):
        """Test successful price update."""
        commodity = create_test_commodity(test_db, name="PriceCommodity9")
        mandi = create_test_mandi(test_db, name="PriceMandi9")
        service = PriceHistoryService(test_db)

        price = service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=date.today(),
            modal_price=100.00,
            min_price=90.00,
            max_price=110.00,
        ))

        update_data = PriceHistoryUpdate(modal_price=200.00)
        result = service.update(price.id, update_data)
        assert result is not None
        assert result.modal_price == 200.00

    def test_delete_success(self, test_db):
        """Test successful price deletion."""
        commodity = create_test_commodity(test_db, name="PriceCommodity10")
        mandi = create_test_mandi(test_db, name="PriceMandi10")
        service = PriceHistoryService(test_db)

        price = service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=date.today(),
            modal_price=100.00,
        ))

        result = service.delete(price.id)
        assert result is True
        assert service.get_by_id(price.id) is None

    def test_count_with_filters(self, test_db):
        """Test count with various filters."""
        commodity = create_test_commodity(test_db, name="PriceCommodity11")
        mandi = create_test_mandi(test_db, name="PriceMandi11")
        service = PriceHistoryService(test_db)

        today = date.today()
        for i in range(5):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=today - timedelta(days=i),
                modal_price=100.00 + i * 10,
            ))

        assert service.count(commodity_id=commodity.id) == 5
        assert service.count(mandi_id=mandi.id) == 5
        assert service.count(
            commodity_id=commodity.id,
            start_date=today - timedelta(days=2),
            end_date=today,
        ) == 3

    def test_pagination(self, test_db):
        """Test pagination in get_all."""
        commodity = create_test_commodity(test_db, name="PriceCommodity12")
        mandi = create_test_mandi(test_db, name="PriceMandi12")
        service = PriceHistoryService(test_db)

        today = date.today()
        for i in range(10):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=today - timedelta(days=i),
                modal_price=100.00 + i,
            ))

        # Get first page
        page1 = service.get_all(commodity_id=commodity.id, skip=0, limit=3)
        assert len(page1) == 3

        # Get second page
        page2 = service.get_all(commodity_id=commodity.id, skip=3, limit=3)
        assert len(page2) == 3

        # Verify different results
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_pagination_limit(self, test_db):
        """Test pagination limits work correctly."""
        commodity = create_test_commodity(test_db, name="PriceCommodity13")
        mandi = create_test_mandi(test_db, name="PriceMandi13")
        service = PriceHistoryService(test_db)

        today = date.today()
        for i in range(5):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=today - timedelta(days=i),
                modal_price=100.00 + i,
            ))

        # Request more than exists
        results = service.get_all(commodity_id=commodity.id, limit=100)
        assert len(results) == 5

        # Request exactly what exists
        results = service.get_all(commodity_id=commodity.id, limit=5)
        assert len(results) == 5

        # Request less than exists
        results = service.get_all(commodity_id=commodity.id, limit=2)
        assert len(results) == 2

    def test_create_with_all_optional_fields(self, test_db):
        """Test creating price with all optional fields."""
        commodity = create_test_commodity(test_db, name="PriceCommodity14")
        mandi = create_test_mandi(test_db, name="PriceMandi14")
        service = PriceHistoryService(test_db)

        price = service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=date.today(),
            modal_price=150.00,
            min_price=120.00,
            max_price=180.00,
        ))

        assert price.modal_price == 150.00
        assert price.min_price == 120.00
        assert price.max_price == 180.00

    def test_create_without_optional_fields(self, test_db):
        """Test creating price without optional min/max fields."""
        commodity = create_test_commodity(test_db, name="PriceCommodity15")
        mandi = create_test_mandi(test_db, name="PriceMandi15")
        service = PriceHistoryService(test_db)

        price = service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=date.today(),
            modal_price=150.00,
        ))

        assert price.modal_price == 150.00
        assert price.min_price is None
        assert price.max_price is None

    def test_get_all_order_by_date_desc(self, test_db):
        """Test get_all returns results ordered by date descending."""
        commodity = create_test_commodity(test_db, name="PriceCommodity16")
        mandi = create_test_mandi(test_db, name="PriceMandi16")
        service = PriceHistoryService(test_db)

        today = date.today()
        # Create in non-chronological order
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=2),
            modal_price=100.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today,
            modal_price=120.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            price_date=today - timedelta(days=1),
            modal_price=110.00,
        ))

        results = service.get_all(commodity_id=commodity.id)
        # Should be ordered by date descending (today first)
        assert results[0].price_date == today
        assert results[1].price_date == today - timedelta(days=1)
        assert results[2].price_date == today - timedelta(days=2)

    def test_get_by_commodity_with_limit(self, test_db):
        """Test get_by_commodity respects limit parameter."""
        commodity = create_test_commodity(test_db, name="PriceCommodity17")
        mandi = create_test_mandi(test_db, name="PriceMandi17")
        service = PriceHistoryService(test_db)

        today = date.today()
        for i in range(5):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=today - timedelta(days=i),
                modal_price=100.00 + i,
            ))

        results = service.get_by_commodity(commodity.id, limit=3)
        assert len(results) == 3

    def test_get_by_mandi_with_limit(self, test_db):
        """Test get_by_mandi respects limit parameter."""
        commodity = create_test_commodity(test_db, name="PriceCommodity18")
        mandi = create_test_mandi(test_db, name="PriceMandi18")
        service = PriceHistoryService(test_db)

        today = date.today()
        for i in range(5):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=today - timedelta(days=i),
                modal_price=100.00 + i,
            ))

        results = service.get_by_mandi(mandi.id, limit=3)
        assert len(results) == 3


class TestHistoricalPricesContinuity:
    """Tests verifying historical price data continuity and gap handling."""

    def test_get_historical_returns_all_dates_in_range(self, test_db):
        """When data exists for 30 consecutive days, all 30 days appear in response."""
        commodity = create_test_commodity(test_db, name="Rice", category="Grains")
        mandi = create_test_mandi(test_db, name="HistMandi1")
        service = PriceHistoryService(test_db)

        # Create 30 consecutive days of data
        base_date = date(2026, 1, 1)
        for i in range(30):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=base_date + timedelta(days=i),
                modal_price=2000.00 + i * 10,
                min_price=1900.00 + i * 10,
                max_price=2100.00 + i * 10,
            ))

        # get_historical_prices returns date-averaged data
        result = service.get_historical_prices(
            commodity="Rice",
            mandi_id=str(mandi.id),
            days=30,
        )

        # Should have data for all 30 days
        assert len(result) == 30, (
            f"Expected 30 days of data, got {len(result)}"
        )

        # Verify dates are in ascending order
        dates = [r["date"] for r in result]
        for i in range(1, len(dates)):
            assert dates[i] > dates[i - 1], "Dates should be ascending"

    def test_get_historical_uses_max_date_as_reference(self, test_db):
        """Historical prices use MAX(price_date) as reference, not today."""
        commodity = create_test_commodity(test_db, name="Wheat", category="Grains")
        mandi = create_test_mandi(test_db, name="HistMandi2")
        service = PriceHistoryService(test_db)

        # Create data for a period in the past (e.g., ending 10 days ago)
        end_date = date.today() - timedelta(days=10)
        for i in range(15):
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=end_date - timedelta(days=i),
                modal_price=3000.00 + i * 5,
            ))

        # Query for 15 days of history
        result = service.get_historical_prices(
            commodity="Wheat",
            mandi_id=str(mandi.id),
            days=15,
        )

        # Should get data, NOT empty (which would happen if reference was today
        # and data is 10+ days old beyond the 15-day window)
        assert len(result) > 0, (
            "Should return data even when latest data is not today"
        )

        # The last date in results should be close to end_date
        last_date = result[-1]["date"]
        assert last_date == end_date, (
            f"Last date should be {end_date}, got {last_date}"
        )

    def test_get_historical_with_gaps_returns_only_existing_dates(self, test_db):
        """When there are gaps in data, only dates with data are returned."""
        commodity = create_test_commodity(test_db, name="Tomato", category="Vegetables")
        mandi = create_test_mandi(test_db, name="HistMandi3")
        service = PriceHistoryService(test_db)

        # Create data with a 3-day gap in the middle
        base_date = date(2026, 1, 1)
        dates_with_data = [0, 1, 2, 6, 7, 8, 9]  # gap at days 3-5
        for i in dates_with_data:
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=base_date + timedelta(days=i),
                modal_price=1500.00 + i * 20,
            ))

        result = service.get_historical_prices(
            commodity="Tomato",
            mandi_id=str(mandi.id),
            days=10,
        )

        # Should only return dates that have data (7 dates, not 10)
        assert len(result) == len(dates_with_data), (
            f"Expected {len(dates_with_data)} dates with data, got {len(result)}"
        )

    def test_get_historical_multiple_mandis_averaged(self, test_db):
        """When mandi_id is 'all', prices from multiple mandis are averaged."""
        commodity = create_test_commodity(test_db, name="Onion", category="Vegetables")
        mandi1 = create_test_mandi(test_db, name="HistMandi4a")
        mandi2 = create_test_mandi(test_db, name="HistMandi4b")
        service = PriceHistoryService(test_db)

        target_date = date(2026, 1, 15)

        # Create prices at two mandis for the same commodity and date
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi1.id,
            price_date=target_date,
            modal_price=1000.00,
        ))
        service.create(PriceHistoryCreate(
            commodity_id=commodity.id,
            mandi_id=mandi2.id,
            price_date=target_date,
            modal_price=2000.00,
        ))

        result = service.get_historical_prices(
            commodity="Onion",
            mandi_id="all",
            days=5,
        )

        # Should have 1 date with averaged price
        assert len(result) == 1
        # Average of 1000 and 2000 = 1500
        assert result[0]["price"] == 1500.00

    def test_get_historical_empty_commodity(self, test_db):
        """Querying a commodity with no data returns empty list."""
        service = PriceHistoryService(test_db)

        result = service.get_historical_prices(
            commodity="NonExistentCrop",
            mandi_id="all",
            days=30,
        )

        assert result == []

    def test_get_historical_price_date_ordering(self, test_db):
        """Results should always be ordered by date ascending."""
        commodity = create_test_commodity(test_db, name="Potato", category="Vegetables")
        mandi = create_test_mandi(test_db, name="HistMandi5")
        service = PriceHistoryService(test_db)

        base_date = date(2026, 1, 1)
        # Create in reverse order
        for i in [9, 3, 7, 1, 5]:
            service.create(PriceHistoryCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                price_date=base_date + timedelta(days=i),
                modal_price=1000.00 + i * 100,
            ))

        result = service.get_historical_prices(
            commodity="Potato",
            mandi_id=str(mandi.id),
            days=15,
        )

        # Verify ascending order
        assert len(result) == 5
        for i in range(1, len(result)):
            assert result[i]["date"] >= result[i - 1]["date"], (
                "Dates should be in ascending order"
            )
