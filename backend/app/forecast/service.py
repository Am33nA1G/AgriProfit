"""
ForecastService — XGBoost + Prophet ensemble serving with cache-first lookup.

Flow:
1. Check forecast_cache for today's cached entry → return immediately on hit
2. Check if trained model meta exists (slug_meta.json) — prefer v4, fall back v3
3. PROD-01 gate: prophet_mape > 5.0 → skip directly to seasonal fallback (corrupted model)
4. Quality gate: R² < 0.3 or Tier D → skip directly to seasonal fallback (FORE-05)
5. Run Prophet + XGBoost ensemble, alpha-weighted by inverse-MAPE
6. PROD-04: Apply interval calibration correction if Prophet coverage < 0.80
7. Cache result and return

Graceful degradation chain (in order):
  Level 1: Full Ensemble       R² ≥ 0.5, tier A/B    → Green/Yellow
  Level 2: Prophet-only        R² ≥ 0.3, tier C       → Yellow
  Level 3: Seasonal stats      {slug}_seasonal.json   → Yellow, "seasonal_average"
  Level 4: National avg        parquet national mean  → Red,    "national_average"
  Level 5: 404                 no data at all         → HTTP 404
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.forecast_cache import ForecastCache
from app.ml.loader import get_or_load_model, load_meta, load_seasonal_stats
from app.forecast.schemas import ForecastResponse, ForecastPoint


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def _build_fourier_exog(date_index: pd.DatetimeIndex) -> pd.DataFrame:
    """8 deterministic Fourier features — identical to training script."""
    doy = date_index.day_of_year.values.astype(float)
    dow = date_index.day_of_week.values.astype(float)
    month = date_index.month.values.astype(float)
    return pd.DataFrame(
        {
            "sin_annual":  np.sin(2 * np.pi * doy / 365.25),
            "cos_annual":  np.cos(2 * np.pi * doy / 365.25),
            "sin_semi":    np.sin(4 * np.pi * doy / 365.25),
            "cos_semi":    np.cos(4 * np.pi * doy / 365.25),
            "sin_weekly":  np.sin(2 * np.pi * dow / 7),
            "cos_weekly":  np.cos(2 * np.pi * dow / 7),
            "sin_monthly": np.sin(2 * np.pi * month / 12),
            "cos_monthly": np.cos(2 * np.pi * month / 12),
        },
        index=date_index,
    )


def mape_to_confidence_colour(mape: Optional[float]) -> str:
    """MAPE-based confidence: Green < 0.15, Yellow 0.15–0.29, Red >= 0.30 or None."""
    if mape is None or mape >= 0.30:
        return "Red"
    if mape < 0.15:
        return "Green"
    return "Yellow"


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
        """Get a forecast for a commodity-district pair."""
        cached = self._lookup_cache(commodity, district, horizon)
        if cached is not None:
            return cached

        slug = _slugify(commodity)
        meta = load_meta(slug)

        # No trained model at all → seasonal fallback
        if meta is None:
            return self._seasonal_fallback(commodity, district, horizon)

        # PROD-01: Block corrupted models before any other gate
        _prophet_mape_gate = meta.get("prophet_mape")
        if _prophet_mape_gate is not None and _prophet_mape_gate > 5.0:
            return self._seasonal_fallback(commodity, district, horizon, reason="corrupted")

        # Quality gate — route to appropriate fallback level
        r2 = meta.get("r2_score", 0.0) or 0.0
        tier = meta.get("tier", "D")
        strategy = meta.get("strategy", "seasonal_average")

        if strategy == "seasonal_average" or tier == "D":
            return self._seasonal_fallback(commodity, district, horizon)

        if r2 < 0.3 and strategy != "prophet_only":
            return self._seasonal_fallback(commodity, district, horizon)

        return self._invoke_model(commodity, district, horizon, meta)

    def _lookup_cache(
        self,
        commodity: str,
        district: str,
        horizon: int,
    ) -> Optional[ForecastResponse]:
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

            # Populate freshness metadata from meta (cheap JSON read — not model load)
            _slug = _slugify(commodity)
            _meta = load_meta(_slug)
            _freshness_days = 0
            _is_stale = False
            _n_markets = 0
            _typical_error_inr = None
            _last_data_date_str = "2025-10-30"
            if _meta is not None:
                _last_data_date_str = _meta.get("last_data_date", "2025-10-30")
                try:
                    _last_date = date.fromisoformat(_last_data_date_str)
                    _freshness_days = (date.today() - _last_date).days
                except (ValueError, TypeError):
                    _freshness_days = 0
                _is_stale = _freshness_days > 30
                _n_markets = len(_meta.get("districts_list", []))
                _prophet_mape = _meta.get("prophet_mape")
                _price_mid = float(row.price_mid) if row.price_mid else 0.0
                _typical_error_inr = (
                    round((_prophet_mape * _price_mid) / 10) * 10
                    if _prophet_mape is not None and _price_mid > 0
                    else None
                )

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
                last_data_date=_last_data_date_str,
                data_freshness_days=_freshness_days,
                is_stale=_is_stale,
                n_markets=_n_markets,
                typical_error_inr=_typical_error_inr,
            )
        except Exception as e:
            logger.warning("Cache lookup failed commodity=%s district=%s: %s", commodity, district, e)
            return None

    def _seasonal_fallback(
        self,
        commodity: str,
        district: str,
        horizon: int,
        reason: Optional[str] = None,
    ) -> ForecastResponse:
        """Return seasonal historical statistics when model quality is insufficient."""
        slug = _slugify(commodity)
        stats = load_seasonal_stats(slug)

        if not stats:
            return self._national_average_fallback(commodity, district, horizon)

        today = date.today()
        points = []
        for d in range(1, horizon + 1):
            forecast_date = today + timedelta(days=d)
            month = forecast_date.month
            month_stats = stats.get(str(month), {})
            mid = month_stats.get("median", month_stats.get("mean", 0.0))
            low = month_stats.get("p25", mid * 0.9 if mid > 0 else 0.0)
            high = month_stats.get("p75", mid * 1.1 if mid > 0 else 0.0)
            points.append(ForecastPoint(
                date=str(forecast_date),
                price_low=round(max(0.0, low), 2),
                price_mid=round(max(0.0, mid), 2),
                price_high=round(max(0.0, high), 2),
            ))

        # PROD-01: corrupted model path overrides confidence and coverage message
        if reason == "corrupted":
            confidence_colour = "Red"
            coverage_message = (
                f"Insufficient data for {commodity} in {district} — seasonal pattern only"
            )
        else:
            confidence_colour = "Yellow"
            coverage_message = (
                f"Model quality insufficient for {commodity}. "
                f"Showing seasonal historical averages."
            )

        return ForecastResponse(
            commodity=commodity,
            district=district,
            horizon_days=horizon,
            direction="flat",
            price_low=points[0].price_low if points else None,
            price_mid=points[0].price_mid if points else None,
            price_high=points[0].price_high if points else None,
            confidence_colour=confidence_colour,
            tier_label="seasonal_average",
            last_data_date="2025-10-30",
            forecast_points=points,
            coverage_message=coverage_message,
            model_version="seasonal",
        )

    def _national_average_fallback(
        self,
        commodity: str,
        district: str,
        horizon: int,
    ) -> ForecastResponse:
        """Last resort: no model and no seasonal data available."""
        return ForecastResponse(
            commodity=commodity,
            district=district,
            horizon_days=horizon,
            direction="flat",
            price_low=None,
            price_mid=None,
            price_high=None,
            confidence_colour="Red",
            tier_label="national_average",
            last_data_date="2025-10-30",
            forecast_points=[],
            coverage_message=(
                f"No forecast model or seasonal data available for {commodity}. "
                f"Please check back after the next model training run."
            ),
        )

    def _invoke_model(
        self,
        commodity: str,
        district: str,
        horizon: int,
        meta: dict,
    ) -> ForecastResponse:
        """Run Prophet + XGBoost ensemble and return a ForecastResponse."""
        slug = _slugify(commodity)
        alpha: float = meta.get("alpha", 1.0)
        r2: Optional[float] = meta.get("r2_score")
        districts_list: list[str] = meta.get("districts_list", [])
        last_data_date: str = meta.get("last_data_date", "2025-10-30")
        prophet_mape: Optional[float] = meta.get("prophet_mape")
        tier: str = meta.get("tier", "B")
        train_exog_columns: list[str] = meta.get("exog_columns", [])
        # PROD-04: default changed from 0.80 to 0.60 for v3-style metas
        interval_coverage: float = meta.get("interval_coverage_80pct", 0.60) or 0.60

        # PROD-05: compute freshness metadata
        try:
            _last_date = date.fromisoformat(last_data_date)
            freshness_days = (date.today() - _last_date).days
        except (ValueError, TypeError):
            freshness_days = 0
        is_stale = freshness_days > 30
        n_markets = len(districts_list)

        # PROD-02: MAPE-only confidence (removes R²-based overrides)
        confidence_colour = mape_to_confidence_colour(prophet_mape)

        prophet_model = get_or_load_model(f"{slug}_prophet")
        if prophet_model is None:
            return self._seasonal_fallback(commodity, district, horizon)

        try:
            # Always predict 365 steps, then slice to requested horizon
            steps = 365
            today = date.today()
            future_dates = pd.date_range(
                pd.Timestamp(today) + pd.Timedelta(days=1),
                periods=steps,
                freq="D",
            )

            # Build future exog: Fourier + climatological normals + Open Meteo (near-term)
            if train_exog_columns:
                try:
                    from app.ml.serving_exog import build_future_exog, align_exog_to_training
                    exog_future = build_future_exog(future_dates[0], steps)
                    exog_future = align_exog_to_training(exog_future, train_exog_columns)
                except Exception as e:
                    logger.warning("Exog build failed slug=%s, using Fourier fallback: %s", slug, e)
                    exog_future = _build_fourier_exog(future_dates)
            else:
                exog_future = _build_fourier_exog(future_dates)

            # Prophet prediction
            future_df = pd.DataFrame({"ds": future_dates})
            prophet_exog_cols = [c for c in exog_future.columns if c in (
                list(_build_fourier_exog(future_dates[:1]).columns) +
                [c for c in exog_future.columns if c.startswith("weather_")]
            )]
            for col in prophet_exog_cols:
                if col in exog_future.columns:
                    future_df[col] = exog_future[col].values

            prophet_result = prophet_model.predict(future_df)
            prophet_mid = prophet_result["yhat"].values
            prophet_lower = prophet_result["yhat_lower"].values
            prophet_upper = prophet_result["yhat_upper"].values

            # PROD-04: Apply interval calibration correction if coverage was poor at training
            # Threshold raised from 0.70 to 0.80 to catch more under-covered models
            if interval_coverage < 0.80 and interval_coverage > 0:
                correction = 0.80 / interval_coverage  # Widen proportionally
                half_span_lower = prophet_mid - prophet_lower
                half_span_upper = prophet_upper - prophet_mid
                prophet_lower = prophet_mid - half_span_lower * correction
                prophet_upper = prophet_mid + half_span_upper * correction

            # XGBoost district-specific prediction
            district_lower = district.lower()
            districts_lower = [d.lower() for d in districts_list]
            xgb_mid: Optional[np.ndarray] = None

            if district_lower in districts_lower and tier in ("A", "B"):
                idx = districts_lower.index(district_lower)
                orig_district = districts_list[idx]
                xgb_model = get_or_load_model(f"{slug}_xgboost")
                if xgb_model is not None:
                    try:
                        xgb_pred = xgb_model.predict(
                            steps=steps,
                            levels=[orig_district],
                            exog=exog_future,
                        )
                        # skforecast 0.20+ returns long-format ['level', 'pred']
                        if "pred" in xgb_pred.columns:
                            xgb_mid = xgb_pred["pred"].values
                        elif orig_district in xgb_pred.columns:
                            xgb_mid = xgb_pred[orig_district].values
                    except Exception as e:
                        logger.warning("XGBoost prediction failed slug=%s district=%s: %s", slug, district, e)
                        xgb_mid = None

            # Ensemble combine
            if xgb_mid is not None:
                ens_mid = alpha * prophet_mid + (1 - alpha) * xgb_mid
                ens_low = np.minimum(prophet_lower, xgb_mid * 0.9)
                ens_high = np.maximum(prophet_upper, xgb_mid * 1.1)
            else:
                ens_mid = prophet_mid
                ens_low = prophet_lower
                ens_high = prophet_upper

            # Slice to requested horizon
            ens_mid = ens_mid[:horizon]
            ens_low = ens_low[:horizon]
            ens_high = ens_high[:horizon]
            future_sliced = future_dates[:horizon]

            # PROD-03: Direction using band-straddling check
            # "up"        = final band entirely or near-entirely above current price
            #               (final_low within 3% of current — limited downside risk)
            # "down"      = final band entirely or near-entirely below current price
            # "uncertain" = band straddles widely (>3% downside AND pct change is small)
            # "flat"      = strong directional pct signal
            if len(ens_mid) >= 2 and ens_mid[0] > 0:
                current_price = ens_mid[0]
                final_low = float(max(0.0, ens_low[-1]))
                final_high = float(ens_high[-1])
                pct = (ens_mid[-1] - current_price) / current_price
                downside_gap = (current_price - final_low) / current_price
                upside_gap = (final_high - current_price) / current_price
                if final_low > current_price or (pct >= 0 and downside_gap <= 0.03):
                    # Band entirely above, or low within 3% of current — heading up
                    direction = "up"
                elif final_high < current_price or (pct <= 0 and upside_gap <= 0.03):
                    # Band entirely below, or high within 3% of current — heading down
                    direction = "down"
                elif abs(pct) <= 0.02:
                    # Small overall trend but wide band straddle — genuinely uncertain
                    direction = "uncertain"
                else:
                    direction = "up" if pct > 0 else "down"
            else:
                direction = "flat"

            # PROD-05: typical_error_inr computed after ens_mid is available
            typical_error_inr = (
                round((prophet_mape * float(ens_mid[0])) / 10) * 10
                if prophet_mape is not None and len(ens_mid) > 0 and float(ens_mid[0]) > 0
                else None
            )

            tier_label = "full model" if tier in ("A", "B") else "prophet_model"

            forecast_points = [
                ForecastPoint(
                    date=str(dt.date()),
                    price_mid=float(ens_mid[i]),
                    price_low=float(max(0.0, ens_low[i])),
                    price_high=float(ens_high[i]),
                )
                for i, dt in enumerate(future_sliced)
            ]

            response = ForecastResponse(
                commodity=commodity,
                district=district,
                horizon_days=horizon,
                direction=direction,
                price_low=float(max(0.0, ens_low[-1])),
                price_mid=float(ens_mid[-1]),
                price_high=float(ens_high[-1]),
                confidence_colour=confidence_colour,
                tier_label=tier_label,
                last_data_date=last_data_date,
                forecast_points=forecast_points,
                r2_score=r2,
                data_freshness_days=freshness_days,
                is_stale=is_stale,
                n_markets=n_markets,
                typical_error_inr=typical_error_inr,
                mape_pct=round(prophet_mape * 100, 1) if prophet_mape is not None else None,
                model_version="legacy",
            )

            self._write_cache(response)
            self._log_forecast(response)
            return response

        except Exception as e:
            logger.error("Model inference failed commodity=%s district=%s: %s", commodity, district, e)
            return self._seasonal_fallback(commodity, district, horizon)

    def _log_forecast(self, response: ForecastResponse) -> None:
        """Record the final-horizon prediction so actual vs predicted can be compared later."""
        from decimal import Decimal
        from app.models.forecast_accuracy_log import ForecastAccuracyLog

        if response.price_mid is None:
            return
        try:
            today = date.today()
            self.db.add(
                ForecastAccuracyLog(
                    commodity_name=response.commodity,
                    district_name=response.district,
                    model_version=response.model_version or "legacy",
                    forecast_date=today,
                    target_date=today + timedelta(days=response.horizon_days),
                    predicted_price=Decimal(str(response.price_mid)),
                )
            )
            self.db.commit()
        except Exception as e:
            logger.warning(
                "Accuracy log write failed commodity=%s district=%s: %s",
                response.commodity, response.district, e,
            )
            self.db.rollback()

    def _write_cache(self, response: ForecastResponse) -> None:
        try:
            from decimal import Decimal

            today = date.today()
            expires = datetime.now(timezone.utc) + timedelta(hours=24)

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
                self.db.add(
                    ForecastCache(
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
                )
            self.db.commit()
        except Exception as e:
            logger.error(
                "Cache write failed commodity=%s district=%s: %s",
                response.commodity, response.district, e,
            )
            self.db.rollback()
