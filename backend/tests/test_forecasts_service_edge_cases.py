import pytest
from uuid import uuid4
from datetime import date, timedelta

from app.forecasts.service import PriceForecastService
from app.forecasts.schemas import PriceForecastCreate, PriceForecastUpdate
from tests.utils import create_test_commodity, create_test_mandi


class TestForecastsServiceEdgeCases:
    """Edge case tests for PriceForecastService."""

    def test_get_by_id_nonexistent(self, test_db):
        """Test getting non-existent forecast returns None."""
        service = PriceForecastService(test_db)
        result = service.get_by_id(uuid4())
        assert result is None

    def test_update_nonexistent(self, test_db):
        """Test updating non-existent forecast returns None."""
        service = PriceForecastService(test_db)
        update_data = PriceForecastUpdate(predicted_price=150.00)
        result = service.update(uuid4(), update_data)
        assert result is None

    def test_delete_nonexistent(self, test_db):
        """Test deleting non-existent forecast returns False."""
        service = PriceForecastService(test_db)
        result = service.delete(uuid4())
        assert result is False

    def test_get_all_empty_results(self, test_db):
        """Test get_all with filters that match nothing."""
        service = PriceForecastService(test_db)
        results = service.get_all(commodity_id=uuid4())
        assert len(results) == 0

    def test_get_all_with_date_range_filter(self, test_db):
        """Test get_all with start_date and end_date filters."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity1")
        mandi = create_test_mandi(test_db, name="ForecastMandi1")
        service = PriceForecastService(test_db)

        today = date.today()
        # Create forecasts for different dates
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=10),
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=5),
            predicted_price=110.00,
            confidence_level=0.90,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today,
            predicted_price=120.00,
            confidence_level=0.95,
            model_version="v1.0",
        ))

        # Filter by date range (should get middle one only)
        results = service.get_all(
            start_date=today - timedelta(days=7),
            end_date=today - timedelta(days=3),
        )
        assert len(results) == 1
        assert results[0].predicted_price == 110.00

    def test_get_latest_when_none_exist(self, test_db):
        """Test get_latest when no forecasts exist."""
        service = PriceForecastService(test_db)
        result = service.get_latest(uuid4(), uuid4())
        assert result is None

    def test_get_latest_with_multiple_forecasts(self, test_db):
        """Test get_latest returns most recent forecast."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity2")
        mandi = create_test_mandi(test_db, name="ForecastMandi2")
        service = PriceForecastService(test_db)

        today = date.today()
        # Create forecasts for different dates
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=5),
            predicted_price=100.00,
            confidence_level=0.80,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today,
            predicted_price=150.00,
            confidence_level=0.95,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=3),
            predicted_price=120.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))

        result = service.get_latest(commodity.id, mandi.id)
        assert result is not None
        assert result.forecast_date == today
        assert result.predicted_price == 150.00

    def test_combined_filters(self, test_db):
        """Test filtering by commodity_id + mandi_id + date range combined."""
        commodity1 = create_test_commodity(test_db, name="ForecastCommodity3")
        commodity2 = create_test_commodity(test_db, name="ForecastCommodity4")
        mandi1 = create_test_mandi(test_db, name="ForecastMandi3")
        mandi2 = create_test_mandi(test_db, name="ForecastMandi4")
        service = PriceForecastService(test_db)

        today = date.today()
        # Create various forecasts
        service.create(PriceForecastCreate(
            commodity_id=commodity1.id,
            mandi_id=mandi1.id,
            forecast_date=today,
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity1.id,
            mandi_id=mandi2.id,
            forecast_date=today,
            predicted_price=110.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity2.id,
            mandi_id=mandi1.id,
            forecast_date=today,
            predicted_price=120.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity1.id,
            mandi_id=mandi1.id,
            forecast_date=today - timedelta(days=30),
            predicted_price=90.00,
            confidence_level=0.80,
            model_version="v1.0",
        ))

        # Filter by commodity + mandi + date range
        results = service.get_all(
            commodity_id=commodity1.id,
            mandi_id=mandi1.id,
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=1),
        )
        assert len(results) == 1
        assert results[0].predicted_price == 100.00

    def test_get_by_commodity_with_date_range(self, test_db):
        """Test get_by_commodity with date range filters."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity5")
        mandi = create_test_mandi(test_db, name="ForecastMandi5")
        service = PriceForecastService(test_db)

        today = date.today()
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=15),
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=5),
            predicted_price=110.00,
            confidence_level=0.90,
            model_version="v1.0",
        ))

        # Get by commodity with date range
        results = service.get_by_commodity(
            commodity.id,
            start_date=today - timedelta(days=10),
            end_date=today,
        )
        assert len(results) == 1
        assert results[0].predicted_price == 110.00

    def test_get_by_mandi_with_date_range(self, test_db):
        """Test get_by_mandi with date range filters."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity6")
        mandi = create_test_mandi(test_db, name="ForecastMandi6")
        service = PriceForecastService(test_db)

        today = date.today()
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=15),
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=5),
            predicted_price=110.00,
            confidence_level=0.90,
            model_version="v1.0",
        ))

        # Get by mandi with date range
        results = service.get_by_mandi(
            mandi.id,
            start_date=today - timedelta(days=10),
            end_date=today,
        )
        assert len(results) == 1
        assert results[0].predicted_price == 110.00

    def test_get_for_date(self, test_db):
        """Test get_for_date returns specific forecast."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity7")
        mandi = create_test_mandi(test_db, name="ForecastMandi7")
        service = PriceForecastService(test_db)

        today = date.today()
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today,
            predicted_price=150.00,
            confidence_level=0.90,
            model_version="v1.0",
        ))

        result = service.get_for_date(commodity.id, mandi.id, today)
        assert result is not None
        assert result.predicted_price == 150.00

    def test_get_for_date_not_found(self, test_db):
        """Test get_for_date returns None when not found."""
        service = PriceForecastService(test_db)
        result = service.get_for_date(uuid4(), uuid4(), date.today())
        assert result is None

    def test_update_with_empty_data(self, test_db):
        """Test update with no changes returns original forecast."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity8")
        mandi = create_test_mandi(test_db, name="ForecastMandi8")
        service = PriceForecastService(test_db)

        forecast = service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=date.today(),
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))

        update_data = PriceForecastUpdate()
        result = service.update(forecast.id, update_data)
        assert result is not None
        assert result.predicted_price == 100.00

    def test_update_success(self, test_db):
        """Test successful forecast update."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity9")
        mandi = create_test_mandi(test_db, name="ForecastMandi9")
        service = PriceForecastService(test_db)

        forecast = service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=date.today(),
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))

        update_data = PriceForecastUpdate(predicted_price=200.00, confidence_level=0.95)
        result = service.update(forecast.id, update_data)
        assert result is not None
        assert float(result.predicted_price) == 200.00
        assert float(result.confidence_level) == 0.95

    def test_delete_success(self, test_db):
        """Test successful forecast deletion."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity10")
        mandi = create_test_mandi(test_db, name="ForecastMandi10")
        service = PriceForecastService(test_db)

        forecast = service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=date.today(),
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v1.0",
        ))

        result = service.delete(forecast.id)
        assert result is True
        assert service.get_by_id(forecast.id) is None

    def test_count_with_filters(self, test_db):
        """Test count with various filters."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity11")
        mandi = create_test_mandi(test_db, name="ForecastMandi11")
        service = PriceForecastService(test_db)

        today = date.today()
        for i in range(5):
            service.create(PriceForecastCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                forecast_date=today - timedelta(days=i),
                predicted_price=100.00 + i * 10,
                confidence_level=0.85,
                model_version="v1.0" if i < 3 else "v2.0",
            ))

        assert service.count(commodity_id=commodity.id) == 5
        assert service.count(mandi_id=mandi.id) == 5
        assert service.count(model_version="v1.0") >= 3
        assert service.count(
            commodity_id=commodity.id,
            start_date=today - timedelta(days=2),
            end_date=today,
        ) == 3

    def test_get_by_model_version(self, test_db):
        """Test get_by_model_version."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity12")
        mandi = create_test_mandi(test_db, name="ForecastMandi12")
        service = PriceForecastService(test_db)

        today = date.today()
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today,
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v3.0-test",
        ))
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today - timedelta(days=1),
            predicted_price=110.00,
            confidence_level=0.90,
            model_version="v4.0-test",
        ))

        results = service.get_by_model_version("v3.0-test")
        assert len(results) == 1
        assert results[0].model_version == "v3.0-test"

    def test_bulk_create(self, test_db):
        """Test bulk creation of forecasts."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity13")
        mandi = create_test_mandi(test_db, name="ForecastMandi13")
        service = PriceForecastService(test_db)

        today = date.today()
        forecasts_data = [
            PriceForecastCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                forecast_date=today - timedelta(days=i),
                predicted_price=100.00 + i * 10,
                confidence_level=0.85,
                model_version="v1.0",
            )
            for i in range(3)
        ]

        results = service.bulk_create(forecasts_data)
        assert len(results) == 3
        assert service.count(commodity_id=commodity.id) >= 3

    def test_pagination(self, test_db):
        """Test pagination in get_all."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity14")
        mandi = create_test_mandi(test_db, name="ForecastMandi14")
        service = PriceForecastService(test_db)

        today = date.today()
        for i in range(10):
            service.create(PriceForecastCreate(
                commodity_id=commodity.id,
                mandi_id=mandi.id,
                forecast_date=today - timedelta(days=i),
                predicted_price=100.00 + i,
                confidence_level=0.85,
                model_version="v1.0",
            ))

        # Get first page
        page1 = service.get_all(commodity_id=commodity.id, skip=0, limit=3)
        assert len(page1) == 3

        # Get second page
        page2 = service.get_all(commodity_id=commodity.id, skip=3, limit=3)
        assert len(page2) == 3

        # Verify different results
        page1_ids = {f.id for f in page1}
        page2_ids = {f.id for f in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_all_with_model_version_filter(self, test_db):
        """Test get_all with model_version filter."""
        commodity = create_test_commodity(test_db, name="ForecastCommodity15")
        mandi = create_test_mandi(test_db, name="ForecastMandi15")
        service = PriceForecastService(test_db)

        today = date.today()
        service.create(PriceForecastCreate(
            commodity_id=commodity.id,
            mandi_id=mandi.id,
            forecast_date=today,
            predicted_price=100.00,
            confidence_level=0.85,
            model_version="v5.0-unique",
        ))

        results = service.get_all(model_version="v5.0-unique")
        assert len(results) == 1
