"""
ForecastService7D — reliable 7-day price forecast using direct multi-step XGBoost.

Architecture:
  1. Check forecast_cache (today's hit → <50ms)
  2. Load v5 7-day model + meta for commodity slug
  3. Query DB for last 60 days of district-level prices
     - Aggregate across mandis within district (median per date)
     - Falls back to parquet-derived history artifact if DB is thin
  4. Build feature vector (lags + rolling stats + calendar + district_enc)
  5. Predict h=1..7 with 7 separate XGBRegressors (direct, not recursive)
  6. Apply empirical residual quantiles for price bands (80% coverage)
  7. Cache result, return ForecastResponse

Fallback: if model missing or <14 days of price history → delegate to
old ForecastService (seasonal stats / national average).

Price bands are derived from per-horizon residual quantiles computed on
the 2024-2025 holdout set during training. 80% empirical coverage
guaranteed at training time.
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.forecast.schemas import ForecastPoint, ForecastResponse
from app.ml.features_7d import FEATURE_COLS, build_serving_vector
from app.ml.loader_7d import load_7d_meta, load_7d_model

if TYPE_CHECKING:
    pass


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def _mape_to_confidence(mape: float | None) -> str:
    """MAPE → colour using h7 (most conservative) horizon."""
    if mape is None or mape >= 0.20:
        return "Red"
    if mape < 0.10:
        return "Green"
    return "Yellow"


# Commodities where the 7-day model is unreliable (MAPE > 30% on holdout).
# These are served via the legacy seasonal fallback instead.
_UNRELIABLE_SLUGS: frozenset[str] = frozenset({
    "coriander_(leaves)",   # 90% MAPE — hyper-perishable, weekly price swings
    "coconut",              # 47% MAPE — count vs weight unit confusion across mandis
    "spinach",              # 33% MAPE — hyper-perishable, supply shocks dominate
})


# ─── DB price query ────────────────────────────────────────────────────────────

_PRICE_QUERY = text("""
    SELECT
        ph.price_date,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ph.modal_price) AS price_modal
    FROM price_history ph
    JOIN mandis m ON ph.mandi_id = m.id
    JOIN commodities c ON ph.commodity_id = c.id
    WHERE LOWER(c.name) LIKE LOWER(:pattern)
      AND LOWER(m.district) = LOWER(:district)
      AND ph.price_date >= :since
      AND ph.modal_price > 0
    GROUP BY ph.price_date
    ORDER BY ph.price_date
""")


def _query_db_prices(
    db: Session,
    commodity: str,
    district: str,
    days: int = 60,
) -> pd.Series:
    """Return a DatetimeIndex pd.Series of daily median prices from the DB.

    Aggregates across all mandis in the district using median (robust to
    outlier mandis). Returns empty Series if no data found.
    """
    since = date.today() - timedelta(days=days)
    # Build a LIKE pattern from the slug: "green_chilli" → "%green chilli%"
    pattern = f"%{commodity.replace('_', ' ')}%"
    try:
        rows = db.execute(
            _PRICE_QUERY,
            {"pattern": pattern, "district": district, "since": since},
        ).fetchall()
    except Exception as e:
        logger.error("DB price query failed commodity=%s district=%s: %s", commodity, district, e)
        return pd.Series(dtype=float)

    if not rows:
        return pd.Series(dtype=float)

    prices = pd.Series(
        {pd.Timestamp(row.price_date): float(row.price_modal) for row in rows},
        dtype=float,
    )
    return prices.sort_index()


# ─── Parquet fallback (recent prices artifact) ─────────────────────────────────

def _load_history_prices(
    slug: str,
    district: str,
    days: int = 60,
) -> pd.Series:
    """Load recent price history from the parquet artifact saved during training.

    Used as cold-start fallback when DB doesn't have sufficient history.
    """
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "artifacts" / "v5" / f"{slug}_7d_history.parquet"
    if not path.exists():
        return pd.Series(dtype=float)

    try:
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["district"].str.lower() == district.lower()]
        if df.empty:
            return pd.Series(dtype=float)
        cutoff = df["date"].max() - pd.Timedelta(days=days)
        df = df[df["date"] >= cutoff]
        return df.set_index("date")["price_modal"].sort_index()
    except Exception as e:
        logger.error("Parquet history load failed slug=%s district=%s: %s", slug, district, e)
        return pd.Series(dtype=float)


# ─── Service ───────────────────────────────────────────────────────────────────

class ForecastService7D:
    """7-day direct multi-step XGBoost forecast service."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def has_model(self, commodity: str) -> bool:
        """Return True if a v5 model exists for this commodity slug."""
        return load_7d_meta(_slugify(commodity)) is not None

    def get_forecast(self, commodity: str, district: str) -> ForecastResponse | None:
        """Return a ForecastResponse for a 7-day forecast.

        Returns None if no v5 model exists (caller should fall back to old service).
        """
        slug = _slugify(commodity)
        if slug in _UNRELIABLE_SLUGS:
            return None  # fall back to legacy seasonal service
        meta = load_7d_meta(slug)
        if meta is None:
            return None

        # Cache check
        cached = self._lookup_cache(commodity, district)
        if cached is not None:
            return cached

        # Resolve district encoding
        encoder: dict = meta.get("district_encoder", {})
        district_lower = district.lower()
        dist_enc = encoder.get(district_lower)
        if dist_enc is None:
            # Unknown district — find closest by name similarity or use median enc
            dist_enc = int(meta.get("unknown_district_enc", 0))

        # Get recent prices: DB first, parquet fallback
        prices = _query_db_prices(self.db, slug, district, days=60)
        if len(prices) < 14:
            prices = _load_history_prices(slug, district, days=60)

        if len(prices) < 14:
            return None  # caller falls back to seasonal

        # Build feature vector from most recent prices
        vec = build_serving_vector(prices, dist_enc)
        if vec is None:
            return None

        # Load models
        models = load_7d_model(slug)
        if models is None:
            return None

        # Predict 7 horizons in log1p space
        log_preds = np.array(
            [float(models[h].predict(vec.reshape(1, -1))[0]) for h in range(1, 8)]
        )

        # Back-transform to price space
        prices_pred = np.expm1(log_preds).clip(min=0.0)

        # Empirical 80% prediction bands (p10/p90 of signed log residuals)
        p10 = np.array([meta.get(f"residual_p10_h{h}", -0.10) for h in range(1, 8)])
        p90 = np.array([meta.get(f"residual_p90_h{h}", 0.10) for h in range(1, 8)])
        prices_low = np.expm1(log_preds + p10).clip(min=0.0)
        prices_high = np.expm1(log_preds + p90).clip(min=0.0)

        # Direction: compare day-7 prediction vs today's price
        current_price = float(prices.iloc[-1])
        final_price = float(prices_pred[-1])
        pct = (final_price - current_price) / max(current_price, 1.0)
        if pct > 0.03:
            direction = "up"
        elif pct < -0.03:
            direction = "down"
        else:
            direction = "flat"

        # Confidence from h7 MAPE (worst horizon = most conservative)
        mape_h7 = meta.get("test_mape_h7")
        confidence_colour = _mape_to_confidence(mape_h7)

        # Freshness — use actual latest price date in the fetched series,
        # not the model meta's training cutoff.  This reflects real data
        # availability so is_stale fires when data.gov.in goes down.
        last_data_date: str = str(prices.index[-1].date())
        freshness_days = (date.today() - prices.index[-1].date()).days

        # typical_error_inr: MAPE × current price, rounded to nearest ₹10
        typical_error_inr = (
            round((mape_h7 * current_price) / 10) * 10
            if mape_h7 is not None and current_price > 0
            else None
        )

        today = date.today()
        forecast_points = [
            ForecastPoint(
                date=str(today + timedelta(days=h)),
                price_mid=round(float(prices_pred[h - 1]), 2),
                price_low=round(float(prices_low[h - 1]), 2),
                price_high=round(float(prices_high[h - 1]), 2),
            )
            for h in range(1, 8)
        ]

        response = ForecastResponse(
            commodity=commodity,
            district=district,
            horizon_days=7,
            direction=direction,
            price_low=round(float(prices_low[-1]), 2),
            price_mid=round(float(prices_pred[-1]), 2),
            price_high=round(float(prices_high[-1]), 2),
            confidence_colour=confidence_colour,
            tier_label="7-day model",
            last_data_date=last_data_date,
            forecast_points=forecast_points,
            r2_score=meta.get("test_r2_h7"),
            data_freshness_days=freshness_days,
            is_stale=freshness_days > 3,
            n_markets=meta.get("n_districts", 0),
            typical_error_inr=typical_error_inr,
            mape_pct=round(mape_h7 * 100, 1) if mape_h7 is not None else None,
            model_version="v5",
        )

        self._write_cache(response)
        self._log_forecast(response)
        return response

    # ── accuracy tracking ──────────────────────────────────────────────────────

    def _log_forecast(self, response: ForecastResponse) -> None:
        """Record the h7 prediction so actual vs predicted can be compared later."""
        from app.models.forecast_accuracy_log import ForecastAccuracyLog

        if response.price_mid is None:
            return
        try:
            today = date.today()
            self.db.add(
                ForecastAccuracyLog(
                    commodity_name=response.commodity,
                    district_name=response.district,
                    model_version=response.model_version or "v5",
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

    # ── cache helpers ──────────────────────────────────────────────────────────

    def _lookup_cache(self, commodity: str, district: str) -> ForecastResponse | None:
        from sqlalchemy import select
        from app.models.forecast_cache import ForecastCache

        try:
            today = date.today()
            now = datetime.now(timezone.utc)
            row = self.db.execute(
                select(ForecastCache).where(
                    ForecastCache.commodity_name == commodity,
                    ForecastCache.district_name == district,
                    ForecastCache.generated_date == today,
                    ForecastCache.forecast_horizon_days == 7,
                    ForecastCache.expires_at > now,
                    ForecastCache.tier_label == "7-day model",
                )
            ).scalar_one_or_none()

            if row is None:
                return None

            slug = _slugify(commodity)
            meta = load_7d_meta(slug)
            freshness_days = 0
            last_data_date = str(today)
            if meta:
                last_data_date = meta.get("last_data_date", str(today))
                try:
                    freshness_days = (
                        today - date.fromisoformat(last_data_date)
                    ).days
                except (ValueError, TypeError):
                    pass

            import json as _json
            pts = []
            if row.forecast_points_json:
                try:
                    pts = [ForecastPoint(**p) for p in _json.loads(row.forecast_points_json)]
                except Exception:
                    pts = []

            return ForecastResponse(
                commodity=row.commodity_name,
                district=row.district_name,
                horizon_days=7,
                direction=row.direction,
                price_low=float(row.price_low) if row.price_low else None,
                price_mid=float(row.price_mid) if row.price_mid else None,
                price_high=float(row.price_high) if row.price_high else None,
                confidence_colour=row.confidence_colour,
                tier_label=row.tier_label,
                last_data_date=last_data_date,
                data_freshness_days=freshness_days,
                is_stale=freshness_days > 30,
                n_markets=meta.get("n_districts", 0) if meta else 0,
                forecast_points=pts,
                model_version="v5",
            )
        except Exception as e:
            logger.warning("Cache lookup failed commodity=%s district=%s: %s", commodity, district, e)
            return None

    def _write_cache(self, response: ForecastResponse) -> None:
        from sqlalchemy import select
        from app.models.forecast_cache import ForecastCache

        try:
            today = date.today()
            expires = datetime.now(timezone.utc) + timedelta(hours=24)

            existing = self.db.execute(
                select(ForecastCache).where(
                    ForecastCache.commodity_name == response.commodity,
                    ForecastCache.district_name == response.district,
                    ForecastCache.generated_date == today,
                    ForecastCache.forecast_horizon_days == 7,
                )
            ).scalar_one_or_none()

            import json as _json
            pts_json = _json.dumps([p.model_dump() for p in response.forecast_points]) if response.forecast_points else None

            if existing:
                existing.direction = response.direction
                existing.price_low = Decimal(str(response.price_low)) if response.price_low else None
                existing.price_mid = Decimal(str(response.price_mid)) if response.price_mid else None
                existing.price_high = Decimal(str(response.price_high)) if response.price_high else None
                existing.confidence_colour = response.confidence_colour
                existing.tier_label = response.tier_label
                existing.forecast_points_json = pts_json
                existing.expires_at = expires
            else:
                self.db.add(
                    ForecastCache(
                        commodity_name=response.commodity,
                        district_name=response.district,
                        generated_date=today,
                        forecast_horizon_days=7,
                        direction=response.direction,
                        price_low=Decimal(str(response.price_low)) if response.price_low else None,
                        price_mid=Decimal(str(response.price_mid)) if response.price_mid else None,
                        price_high=Decimal(str(response.price_high)) if response.price_high else None,
                        confidence_colour=response.confidence_colour,
                        tier_label=response.tier_label,
                        forecast_points_json=pts_json,
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
