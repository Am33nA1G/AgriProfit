"""
ForecastService — forecast serving with cache-first lookup, model invocation,
and seasonal fallback routing.

Flow:
1. Check forecast_cache for today's cached entry → return immediately on hit
2. Check coverage_days for this commodity+district
3. If coverage < 365 days → return seasonal fallback (FORE-05)
4. Load model via get_or_load_model()
5. If model missing → return seasonal fallback
6. Call forecaster.predict_interval(), compute direction, cache, return
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.forecast_cache import ForecastCache
from app.ml.loader import get_or_load_model
from app.forecast.schemas import ForecastResponse, ForecastPoint

MIN_DAYS_SERVE = 365   # FORE-05: below this → seasonal fallback


def mape_to_confidence_colour(mape: Optional[float]) -> str:
    """Map MAPE value to a confidence colour for the UI.

    Green: MAPE < 10% (high confidence)
    Yellow: 10% <= MAPE < 25% (moderate confidence)
    Red: MAPE >= 25% or None (low confidence / missing data)
    """
    if mape is None:
        return "Red"
    if mape < 0.10:
        return "Green"
    if mape < 0.25:
        return "Yellow"
    return "Red"


class ForecastService:
    """Service layer for price forecast retrieval."""

    def __init__(self, db: Session):
        self.db = db

    def get_forecast(
        self,
        commodity: str,
        district: str,
        horizon: int = 14,
    ) -> ForecastResponse:
        """Get a forecast for a commodity-district pair.

        Priority:
        1. Cache hit → return cached response
        2. Insufficient data → seasonal fallback
        3. Model available → run prediction
        4. Model missing → seasonal fallback
        """
        # 1. Cache lookup
        cached = self._lookup_cache(commodity, district, horizon)
        if cached is not None:
            return cached

        # 2. Coverage check
        coverage_days = self._get_coverage_days(commodity, district)
        if coverage_days < MIN_DAYS_SERVE:
            return self._seasonal_fallback(commodity, district, horizon)

        # 3. Load model
        slug = commodity.lower().replace(" ", "_").replace("/", "_")
        model = get_or_load_model(slug)
        if model is None:
            return self._seasonal_fallback(commodity, district, horizon)

        # 4. Invoke model
        return self._invoke_model(model, commodity, district, horizon)

    def _lookup_cache(
        self,
        commodity: str,
        district: str,
        horizon: int,
    ) -> Optional[ForecastResponse]:
        """Check forecast_cache for a valid (non-expired) entry for today."""
        try:
            today = date.today()
            now = datetime.now(timezone.utc)

            row = self.db.execute(
                select(ForecastCache).where(
                    ForecastCache.commodity_name == commodity,
                    ForecastCache.district_name == district,
                    ForecastCache.generated_date == today,
                    ForecastCache.forecast_horizon_days == horizon,
                    ForecastCache.expires_at > now,
                )
            ).scalar_one_or_none()

            if row is None:
                return None

            return ForecastResponse(
                commodity=row.commodity_name,
                district=row.district_name,
                horizon_days=row.forecast_horizon_days,
                direction=row.direction,
                price_low=float(row.price_low) if row.price_low else None,
                price_mid=float(row.price_mid) if row.price_mid else None,
                price_high=float(row.price_high) if row.price_high else None,
                confidence_colour=row.confidence_colour,
                tier_label=row.tier_label,
                last_data_date="2025-10-30",
            )
        except Exception:
            return None

    def _seasonal_fallback(
        self,
        commodity: str,
        district: str,
        horizon: int,
    ) -> ForecastResponse:
        """Return a seasonal average fallback response (FORE-05)."""
        return ForecastResponse(
            commodity=commodity,
            district=district,
            horizon_days=horizon,
            direction="flat",
            price_low=None,
            price_mid=None,
            price_high=None,
            confidence_colour="Red",
            tier_label="seasonal average fallback",
            last_data_date="2025-10-30",
            coverage_message=(
                f"Insufficient price history for {district}. "
                f"Showing seasonal averages."
            ),
        )

    def _get_coverage_days(self, commodity: str, district: str) -> int:
        """Count the date span for this commodity+district pair in price_history."""
        try:
            from app.models.price_history import PriceHistory

            result = self.db.execute(
                select(
                    func.min(PriceHistory.price_date),
                    func.max(PriceHistory.price_date),
                ).where(
                    PriceHistory.commodity_name == commodity,
                    PriceHistory.district == district,
                )
            ).one_or_none()

            if result is None or result[0] is None or result[1] is None:
                return 0

            return (result[1] - result[0]).days
        except Exception:
            return 0

    def _invoke_model(
        self,
        model,
        commodity: str,
        district: str,
        horizon: int,
    ) -> ForecastResponse:
        """Call predict_interval on the loaded model and build the response."""
        try:
            # Predict with interval
            predictions = model.predict_interval(
                steps=horizon,
                levels=[district],
                interval=[10, 90],
                n_boot=100,
            )

            # Extract values for the last forecast day
            if len(predictions) > 0:
                last_row = predictions.iloc[-1]
                col_names = predictions.columns.tolist()

                # skforecast column naming: {level}, {level}_lower_bound, {level}_upper_bound
                mid_col = district
                low_col = f"{district}_lower_bound"
                high_col = f"{district}_upper_bound"

                price_mid = float(last_row[mid_col]) if mid_col in col_names else None
                price_low = float(last_row[low_col]) if low_col in col_names else None
                price_high = float(last_row[high_col]) if high_col in col_names else None
            else:
                price_mid = price_low = price_high = None

            # Determine direction by comparing first and last predicted mid values
            if len(predictions) >= 2:
                first_mid = float(predictions[district].iloc[0])
                last_mid = float(predictions[district].iloc[-1])
                pct_change = (last_mid - first_mid) / first_mid if first_mid != 0 else 0
                if pct_change > 0.02:
                    direction = "up"
                elif pct_change < -0.02:
                    direction = "down"
                else:
                    direction = "flat"
            else:
                direction = "flat"

            # Build forecast points for the chart
            forecast_points = []
            for idx, row in predictions.iterrows():
                point = ForecastPoint(
                    date=str(idx.date()) if hasattr(idx, "date") else str(idx),
                    price_mid=float(row[district]) if district in predictions.columns else None,
                    price_low=float(row[f"{district}_lower_bound"]) if f"{district}_lower_bound" in predictions.columns else None,
                    price_high=float(row[f"{district}_upper_bound"]) if f"{district}_upper_bound" in predictions.columns else None,
                )
                forecast_points.append(point)

            # Confidence colour from model training log
            confidence_colour = self._get_confidence_colour(commodity)

            response = ForecastResponse(
                commodity=commodity,
                district=district,
                horizon_days=horizon,
                direction=direction,
                price_low=price_low,
                price_mid=price_mid,
                price_high=price_high,
                confidence_colour=confidence_colour,
                tier_label="full model",
                last_data_date="2025-10-30",
                forecast_points=forecast_points,
            )

            # Cache the result
            self._write_cache(response)

            return response

        except Exception as e:
            # If model invocation fails, fallback to seasonal
            return self._seasonal_fallback(commodity, district, horizon)

    def _get_confidence_colour(self, commodity: str) -> str:
        """Look up MAPE from model_training_log for this commodity."""
        try:
            from app.models.model_training_log import ModelTrainingLog

            row = self.db.execute(
                select(ModelTrainingLog.mape_mean)
                .where(ModelTrainingLog.commodity == commodity)
                .order_by(ModelTrainingLog.trained_at.desc())
                .limit(1)
            ).scalar_one_or_none()

            if row is not None:
                return mape_to_confidence_colour(float(row))
            return "Yellow"
        except Exception:
            return "Yellow"

    def _write_cache(self, response: ForecastResponse) -> None:
        """Upsert the forecast response into forecast_cache."""
        try:
            from decimal import Decimal

            today = date.today()
            expires = datetime.now(timezone.utc) + timedelta(hours=24)

            # Check for existing entry
            existing = self.db.execute(
                select(ForecastCache).where(
                    ForecastCache.commodity_name == response.commodity,
                    ForecastCache.district_name == response.district,
                    ForecastCache.generated_date == today,
                )
            ).scalar_one_or_none()

            if existing:
                existing.direction = response.direction
                existing.price_low = Decimal(str(response.price_low)) if response.price_low else None
                existing.price_mid = Decimal(str(response.price_mid)) if response.price_mid else None
                existing.price_high = Decimal(str(response.price_high)) if response.price_high else None
                existing.confidence_colour = response.confidence_colour
                existing.tier_label = response.tier_label
                existing.expires_at = expires
            else:
                cache_entry = ForecastCache(
                    commodity_name=response.commodity,
                    district_name=response.district,
                    generated_date=today,
                    forecast_horizon_days=response.horizon_days,
                    direction=response.direction,
                    price_low=Decimal(str(response.price_low)) if response.price_low else None,
                    price_mid=Decimal(str(response.price_mid)) if response.price_mid else None,
                    price_high=Decimal(str(response.price_high)) if response.price_high else None,
                    confidence_colour=response.confidence_colour,
                    tier_label=response.tier_label,
                    expires_at=expires,
                )
                self.db.add(cache_entry)

            self.db.commit()
        except Exception:
            self.db.rollback()
