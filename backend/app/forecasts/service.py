from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import PriceForecast
from app.forecasts.schemas import PriceForecastCreate, PriceForecastUpdate


class PriceForecastService:
    """Service class for PriceForecast operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, forecast_data: PriceForecastCreate) -> PriceForecast:
        """Create a new price forecast."""
        try:
            forecast = PriceForecast(
                commodity_id=forecast_data.commodity_id,
                mandi_id=forecast_data.mandi_id,
                forecast_date=forecast_data.forecast_date,
                predicted_price=forecast_data.predicted_price,
                confidence_level=forecast_data.confidence_level,
                model_version=forecast_data.model_version,
            )
            self.db.add(forecast)
            self.db.commit()
            self.db.refresh(forecast)
            return forecast
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Forecast for this commodity, mandi, and date already exists")
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, forecast_id: UUID) -> PriceForecast | None:
        """Get a single price forecast by ID."""
        return self.db.query(PriceForecast).filter(PriceForecast.id == forecast_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        commodity_id: UUID | None = None,
        mandi_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        model_version: str | None = None,
    ) -> list[PriceForecast]:
        """Get price forecasts with optional filtering."""
        query = self.db.query(PriceForecast)

        if commodity_id:
            query = query.filter(PriceForecast.commodity_id == commodity_id)

        if mandi_id:
            query = query.filter(PriceForecast.mandi_id == mandi_id)

        if start_date:
            query = query.filter(PriceForecast.forecast_date >= start_date)

        if end_date:
            query = query.filter(PriceForecast.forecast_date <= end_date)

        if model_version:
            query = query.filter(PriceForecast.model_version == model_version)

        return query.order_by(PriceForecast.forecast_date.desc()).offset(skip).limit(limit).all()

    def get_latest(self, commodity_id: UUID, mandi_id: UUID) -> PriceForecast | None:
        """Get the latest forecast for a commodity at a mandi."""
        return self.db.query(PriceForecast).filter(
            PriceForecast.commodity_id == commodity_id,
            PriceForecast.mandi_id == mandi_id,
        ).order_by(PriceForecast.forecast_date.desc()).first()

    def get_by_commodity(
        self,
        commodity_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[PriceForecast]:
        """Get all forecasts for a specific commodity."""
        query = self.db.query(PriceForecast).filter(PriceForecast.commodity_id == commodity_id)

        if start_date:
            query = query.filter(PriceForecast.forecast_date >= start_date)

        if end_date:
            query = query.filter(PriceForecast.forecast_date <= end_date)

        return query.order_by(PriceForecast.forecast_date.desc()).limit(limit).all()

    def get_by_mandi(
        self,
        mandi_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[PriceForecast]:
        """Get all forecasts for a specific mandi."""
        query = self.db.query(PriceForecast).filter(PriceForecast.mandi_id == mandi_id)

        if start_date:
            query = query.filter(PriceForecast.forecast_date >= start_date)

        if end_date:
            query = query.filter(PriceForecast.forecast_date <= end_date)

        return query.order_by(PriceForecast.forecast_date.desc()).limit(limit).all()

    def get_for_date(
        self,
        commodity_id: UUID,
        mandi_id: UUID,
        forecast_date: date,
    ) -> PriceForecast | None:
        """Get forecast for a specific commodity, mandi, and date."""
        return self.db.query(PriceForecast).filter(
            PriceForecast.commodity_id == commodity_id,
            PriceForecast.mandi_id == mandi_id,
            PriceForecast.forecast_date == forecast_date,
        ).first()

    def update(self, forecast_id: UUID, forecast_data: PriceForecastUpdate) -> PriceForecast | None:
        """Update an existing price forecast."""
        forecast = self.db.query(PriceForecast).filter(PriceForecast.id == forecast_id).first()

        if not forecast:
            return None

        update_data = forecast_data.model_dump(exclude_unset=True)

        if not update_data:
            return forecast

        try:
            for field, value in update_data.items():
                setattr(forecast, field, value)

            self.db.commit()
            self.db.refresh(forecast)
            return forecast
        except Exception:
            self.db.rollback()
            raise

    def delete(self, forecast_id: UUID) -> bool:
        """Hard delete a price forecast."""
        forecast = self.db.query(PriceForecast).filter(PriceForecast.id == forecast_id).first()

        if not forecast:
            return False

        try:
            self.db.delete(forecast)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def count(
        self,
        commodity_id: UUID | None = None,
        mandi_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        model_version: str | None = None,
    ) -> int:
        """Count price forecasts with optional filtering."""
        query = self.db.query(PriceForecast)

        if commodity_id:
            query = query.filter(PriceForecast.commodity_id == commodity_id)

        if mandi_id:
            query = query.filter(PriceForecast.mandi_id == mandi_id)

        if start_date:
            query = query.filter(PriceForecast.forecast_date >= start_date)

        if end_date:
            query = query.filter(PriceForecast.forecast_date <= end_date)

        if model_version:
            query = query.filter(PriceForecast.model_version == model_version)

        return query.count()

    def get_by_model_version(
        self,
        model_version: str,
        limit: int = 100,
    ) -> list[PriceForecast]:
        """Get all forecasts for a specific model version."""
        return self.db.query(PriceForecast).filter(
            PriceForecast.model_version == model_version,
        ).order_by(PriceForecast.forecast_date.desc()).limit(limit).all()

    def bulk_create(self, forecasts_data: list[PriceForecastCreate]) -> list[PriceForecast]:
        """Create multiple forecasts in a single transaction."""
        try:
            forecasts = [
                PriceForecast(
                    commodity_id=data.commodity_id,
                    mandi_id=data.mandi_id,
                    forecast_date=data.forecast_date,
                    predicted_price=data.predicted_price,
                    confidence_level=data.confidence_level,
                    model_version=data.model_version,
                )
                for data in forecasts_data
            ]
            self.db.add_all(forecasts)
            self.db.commit()
            for forecast in forecasts:
                self.db.refresh(forecast)
            return forecasts
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Duplicate forecast entries detected")
        except Exception:
            self.db.rollback()
            raise