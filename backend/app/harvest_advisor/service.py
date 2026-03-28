"""Harvest advisor service -- crop recommendations and weather warnings."""
from __future__ import annotations
import calendar
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.harvest_advisor.schemas import (
    CropRecommendation,
    HarvestAdvisorResponse,
    WeatherWarning,
)
from app.harvest_advisor.crop_calendar import (
    CROP_CALENDAR,
    get_crops_for_season,
)
from app.harvest_advisor.model_loader import load_yield_model, get_crop_category
from app.harvest_advisor.weather_warnings import generate_all_warnings
from app.harvest_advisor.input_costs import (
    CROP_INPUT_COSTS,
    DEFAULT_INPUT_COST,
    CROP_YIELD_BOUNDS,
    DEFAULT_YIELD_BOUNDS,
)
from sqlalchemy import text
from app.forecast.service import ForecastService

logger = logging.getLogger(__name__)


def format_month_range(months: list[int]) -> str:
    """Format [6, 7] -> 'Jun \u2013 Jul' using calendar.month_abbr."""
    return f"{calendar.month_abbr[months[0]]} \u2013 {calendar.month_abbr[months[1]]}"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data"

DISCLAIMER = (
    "These recommendations are indicative only, based on historical price models and "
    "synthetic yield data. Always consult local agricultural extension officers before "
    "making planting decisions. Market prices are subject to change."
)

# Perennial fruit crops that should only appear in annual season queries
PERENNIAL_CROPS: frozenset[str] = frozenset({
    "mango", "banana", "grapes", "orange", "pomegranate",
})


def _load_parquet_safe(path: Path) -> Optional[pd.DataFrame]:
    """Load parquet file, return None if missing or invalid."""
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path, engine="pyarrow")
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def _load_csv_safe(path: Path) -> Optional[pd.DataFrame]:
    """Load CSV file, return None if missing or invalid."""
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def _r2_to_confidence(r2: float) -> str:
    """
    Convert hold-out R² to a 3-tier confidence label.

    Thresholds (ICAR agronomic modelling norms):
      R² >= 0.70 → "high"    — model explains >70% of yield variance
      R² >= 0.40 → "medium"  — useful signal but notable uncertainty
      R²  < 0.40 → "low"     — unreliable; prefer historical average fallback
    """
    if r2 >= 0.70:
        return "high"
    if r2 >= 0.40:
        return "medium"
    return "low"


class HarvestAdvisorService:
    """Main service for harvest recommendations."""

    def __init__(self, db: Session):
        self.db = db

    def _get_soil_features(
        self, district: str, state: str, soil_df: Optional[pd.DataFrame]
    ) -> dict:
        """Get soil features for a district, fall back to state average."""
        if soil_df is None or soil_df.empty:
            return {"N_kg_ha": None, "P_kg_ha": None, "K_kg_ha": None, "pH": None}

        dist_mask = soil_df["district"].str.lower() == district.lower()
        row = soil_df[dist_mask]
        if row.empty:
            # State fallback
            state_mask = soil_df["state"].str.lower() == state.lower()
            row = soil_df[state_mask]
        if row.empty:
            return {"N_kg_ha": None, "P_kg_ha": None, "K_kg_ha": None, "pH": None}

        r = row.iloc[0]
        return {
            "N_kg_ha": float(r.get("N_kg_ha", np.nan)) if not pd.isna(r.get("N_kg_ha", np.nan)) else None,
            "P_kg_ha": float(r.get("P_kg_ha", np.nan)) if not pd.isna(r.get("P_kg_ha", np.nan)) else None,
            "K_kg_ha": float(r.get("K_kg_ha", np.nan)) if not pd.isna(r.get("K_kg_ha", np.nan)) else None,
            "pH": float(r.get("pH", np.nan)) if not pd.isna(r.get("pH", np.nan)) else None,
        }

    def _get_weather_features(
        self, district: str, weather_monthly_df: Optional[pd.DataFrame]
    ) -> dict:
        """Get annual-average weather features for a district."""
        defaults = {
            "annual_rainfall_mm": None,
            "annual_rainfall_deviation_pct": None,
            "avg_temp_c": None,
            "avg_humidity": None,
        }
        if weather_monthly_df is None or weather_monthly_df.empty:
            return defaults

        mask = weather_monthly_df["district"].str.lower() == district.lower()
        dist_data = weather_monthly_df[mask]
        if dist_data.empty:
            return defaults

        # Use last 3 years
        recent = dist_data.sort_values(["year", "month"]).tail(36)
        return {
            "annual_rainfall_mm": float(recent["rainfall_mm"].sum()) if "rainfall_mm" in recent.columns else None,
            "annual_rainfall_deviation_pct": float(recent["rainfall_deviation_pct"].mean()) if "rainfall_deviation_pct" in recent.columns else None,
            "avg_temp_c": float(recent["avg_temp_c"].mean()) if "avg_temp_c" in recent.columns else None,
            "avg_humidity": float(recent["avg_humidity"].mean()) if "avg_humidity" in recent.columns else None,
        }

    @staticmethod
    def _clamp_yield(crop: str, raw_yield: float, confidence: str) -> tuple[float, str]:
        """
        Clamp a yield prediction to ICAR-sourced physical bounds.
        Downgrades confidence to 'low' if clamping was required.
        """
        lo, hi = CROP_YIELD_BOUNDS.get(crop, DEFAULT_YIELD_BOUNDS)
        clamped = max(lo, min(raw_yield, hi))
        if clamped != raw_yield:
            logger.warning(
                "Yield for %s clamped %.0f → %.0f kg/ha (bounds: %.0f–%.0f)",
                crop, raw_yield, clamped, lo, hi,
            )
            return clamped, "low"
        return clamped, confidence

    def _predict_yield(
        self,
        crop: str,
        district: str,
        soil: dict,
        weather: dict,
        yield_df: Optional[pd.DataFrame],
    ) -> tuple[float, str]:
        """
        Predict yield_kg_ha for a crop. Returns (yield, confidence).

        Strategy:
        - If the district is known to the ML model, use the ML prediction.
        - If the district is unknown (out-of-training), the ML model extrapolates
          with a zeroed district encoding and produces unreliable results.
          In that case, skip directly to the historical national average from yield_df.
        - Final fallback: hardcoded generic defaults.
        All predictions are clamped to ICAR physical bounds before returning.
        """
        category = get_crop_category(crop)

        if category:
            model_dict = load_yield_model(category, crop_name=crop)
            if model_dict:
                try:
                    feature_names = model_dict["feature_names"]
                    features: dict = {
                        "N_kg_ha": soil.get("N_kg_ha"),
                        "P_kg_ha": soil.get("P_kg_ha"),
                        "K_kg_ha": soil.get("K_kg_ha"),
                        "pH": soil.get("pH"),
                        "annual_rainfall_mm": weather.get("annual_rainfall_mm"),
                        "annual_rainfall_deviation_pct": weather.get("annual_rainfall_deviation_pct"),
                        "avg_temp_c": weather.get("avg_temp_c"),
                        "avg_humidity": weather.get("avg_humidity"),
                    }

                    # Encode crop
                    if "crop_encoded" in feature_names:
                        crop_encoder = model_dict.get("crop_encoder")
                        if crop_encoder is not None:
                            try:
                                features["crop_encoded"] = int(
                                    crop_encoder.transform([crop.lower()])[0]
                                )
                            except ValueError:
                                features["crop_encoded"] = 0
                        else:
                            features["crop_encoded"] = 0

                    # Encode district — track whether district is known to the model
                    district_known = True
                    if "district_encoded" in feature_names:
                        district_encoder = model_dict.get("district_encoder")
                        if district_encoder is not None:
                            try:
                                features["district_encoded"] = int(
                                    district_encoder.transform([district.lower()])[0]
                                )
                            except ValueError:
                                # District not in training data → skip ML, use historical avg
                                district_known = False
                                logger.debug(
                                    "District '%s' not in yield model — using historical average for %s",
                                    district, crop,
                                )
                        else:
                            district_known = False

                    # If district is unknown, ML prediction is pure extrapolation — skip it
                    if not district_known:
                        raise ValueError(f"district '{district}' not in training data")

                    # Historical 5-year average yield for this crop (used as a feature)
                    if "yield_5yr_avg" in feature_names:
                        if yield_df is not None and not yield_df.empty and "yield_5yr_avg" in yield_df.columns:
                            mask = yield_df["crop_name"].str.lower() == crop.lower()
                            avg_5yr = yield_df.loc[mask, "yield_5yr_avg"].mean()
                            features["yield_5yr_avg"] = float(avg_5yr) if not np.isnan(avg_5yr) else np.nan
                        else:
                            features["yield_5yr_avg"] = np.nan

                    X = np.array([[features.get(f, np.nan) for f in feature_names]])
                    X = np.nan_to_num(X, nan=0.0)
                    scaler = model_dict.get("scaler")
                    if scaler:
                        X = scaler.transform(X)
                    model = model_dict["model"]
                    pred = float(model.predict(X)[0])
                    r2 = model_dict.get("test_r2", model_dict.get("cv_r2_mean", 0))
                    confidence = _r2_to_confidence(r2)
                    return self._clamp_yield(crop, pred, confidence)
                except Exception as e:
                    logger.debug(f"Yield model skipped for {crop}: {e}")

        # Fallback: historical national average from yield_df
        if yield_df is not None and not yield_df.empty:
            mask = yield_df["crop_name"].str.lower() == crop.lower()
            crop_data = yield_df[mask]
            if not crop_data.empty:
                avg = float(crop_data["yield_kg_ha"].mean())
                return self._clamp_yield(crop, avg, "low")

        # Final fallback: generic defaults per crop type
        DEFAULTS = {
            "rice": 2500, "wheat": 3000, "maize": 2800, "cotton": 1800,
            "onion": 15000, "tomato": 20000, "potato": 18000, "brinjal": 12000,
            "cauliflower": 10000, "carrot": 10000, "mustard": 1200, "groundnut": 1500,
            "soybean": 1200, "sunflower": 1000, "arhar": 1100, "moong": 800,
            "urad": 900, "chana": 900, "mango": 5000, "banana": 25000,
        }
        raw = float(DEFAULTS.get(crop, 1500))
        return self._clamp_yield(crop, raw, "low")

    def _get_historical_state_price(self, crop: str, state: str) -> tuple[float | None, int]:
        """
        Query seasonal_price_stats for a weighted annual median price.

        Returns (weighted_median_price, total_record_count).
        Returns (None, 0) when no data exists for the crop+state combination.
        This is more reliable than the forecast model for planning purposes —
        it reflects actual traded prices from up to 10 years of Agmarknet data.
        """
        rows = self.db.execute(
            text("""
                SELECT median_price, record_count
                FROM seasonal_price_stats
                WHERE LOWER(commodity_name) = LOWER(:crop)
                  AND LOWER(state_name) = LOWER(:state)
            """),
            {"crop": crop, "state": state},
        ).fetchall()

        if not rows:
            return None, 0

        total_records = sum(r.record_count for r in rows)
        if total_records == 0:
            return None, 0

        weighted_price = sum(r.median_price * r.record_count for r in rows) / total_records
        return float(weighted_price), total_records

    def _get_price_forecast(
        self,
        crop: str,
        district: str,
        state: str,
        hist_price: float | None = None,
        record_count: int = 0,
    ) -> tuple[float, str, str]:
        """
        Get expected price per quintal for planning purposes.
        Returns (price, direction, confidence_colour).

        Priority:
        1. Historical state-level median from seasonal_price_stats (most reliable for planning)
        2. ForecastService ML result (if it has actual price data)
        3. Hardcoded PRICE_FALLBACK (last resort)

        hist_price / record_count can be pre-supplied to avoid a redundant DB query.
        """
        # Priority 1: real historical median from the DB (seasonal_price_stats)
        if hist_price is None:
            hist_price, record_count = self._get_historical_state_price(crop, state)
        if hist_price is not None:
            # Enough records → Green confidence; thin data → Yellow
            colour = "Green" if record_count >= 500 else "Yellow"
            return hist_price, "flat", colour

        # Priority 2: ML forecast model
        try:
            svc = ForecastService(self.db)
            result = svc.get_forecast(crop, district, horizon=14)
            if result.price_mid is not None or result.price_low is not None:
                price = float(result.price_mid if result.price_mid is not None else result.price_low)
                return price, result.direction, result.confidence_colour
        except Exception:
            pass

        # Priority 3: static fallback
        PRICE_FALLBACK = {
            "rice": 2200, "wheat": 2100, "maize": 1800, "cotton": 6000,
            "onion": 1500, "tomato": 1200, "potato": 900, "brinjal": 1000,
            "cauliflower": 800, "carrot": 1500, "mustard": 5500, "groundnut": 5000,
            "soybean": 4000, "sunflower": 4200, "arhar": 6200, "moong": 7500,
            "urad": 7000, "chana": 5000, "mango": 3000, "banana": 1500,
        }
        return float(PRICE_FALLBACK.get(crop, 2000)), "flat", "Yellow"

    def _soil_suitability_note(self, crop: str, soil: dict) -> Optional[str]:
        """Generate a soil suitability note if nutrient levels are suboptimal."""
        n = soil.get("N_kg_ha")
        p = soil.get("P_kg_ha")
        notes = []
        if n is not None and n < 50:
            notes.append("Low N -- apply nitrogen fertiliser before sowing")
        if p is not None and p < 10:
            notes.append("Low P -- apply phosphate fertiliser")
        return "; ".join(notes) if notes else None

    def compute_recommendation(
        self, state: str, district: str, season: str
    ) -> HarvestAdvisorResponse:
        """Main recommendation computation."""
        coverage_notes: list[str] = []

        # Load data files lazily
        soil_df = _load_parquet_safe(DATA_DIR / "soil-health" / "district_soil_aggregated.parquet")
        weather_monthly_df = _load_parquet_safe(DATA_DIR / "features" / "weather_monthly_features.parquet")
        rainfall_df = _load_parquet_safe(DATA_DIR / "ranifall_data" / "combined" / "rainfall_district_monthly.parquet")
        weather_csv_df = _load_csv_safe(DATA_DIR / "weather data" / "india_weather_daily_10years.csv")
        yield_df = _load_parquet_safe(DATA_DIR / "features" / "yield_training_matrix.parquet")

        if soil_df is None:
            coverage_notes.append("Soil data not available -- using default nutrient assumptions.")
        if yield_df is None:
            coverage_notes.append("Yield model data not available -- using crop average yields.")
        if weather_monthly_df is None:
            coverage_notes.append("Weather data not available -- using regional averages.")

        # Get soil and weather features
        soil = self._get_soil_features(district, state, soil_df)
        weather = self._get_weather_features(district, weather_monthly_df)

        # Get weather warnings
        warnings, spi, drought_risk = generate_all_warnings(
            district, state, self.db, rainfall_df, weather_csv_df
        )

        # Get crops for season and compute profits
        crops = get_crops_for_season(season)
        if season != "annual":
            crops = [c for c in crops if c not in PERENNIAL_CROPS]
        recommendations: list[CropRecommendation] = []
        forecast_available = False

        for crop in crops:
            yield_kg_ha, yield_confidence = self._predict_yield(crop, district, soil, weather, yield_df)

            # Resolve historical price once — reused for both price and market-data check
            hist_price, record_count = self._get_historical_state_price(crop, state)
            has_market_data = record_count > 0
            price_per_quintal, direction, colour = self._get_price_forecast(
                crop, district, state, hist_price=hist_price, record_count=record_count
            )
            if colour != "Yellow":
                forecast_available = True

            gross_revenue = (yield_kg_ha / 100.0) * price_per_quintal
            input_cost = CROP_INPUT_COSTS.get(crop, DEFAULT_INPUT_COST)
            net_profit = gross_revenue - input_cost

            cal = CROP_CALENDAR[crop]
            recommendations.append(CropRecommendation(
                crop_name=crop.capitalize(),
                rank=0,  # Will be set after sorting
                gross_revenue_per_ha=round(gross_revenue, 2),
                input_cost_per_ha=float(input_cost),
                expected_profit_per_ha=round(net_profit, 2),
                expected_yield_kg_ha=round(yield_kg_ha, 2),
                expected_price_per_quintal=round(price_per_quintal, 2),
                yield_confidence=yield_confidence,
                price_direction=direction,
                price_confidence_colour=colour,
                sowing_window=format_month_range(cal["sow"]),
                harvest_window=format_month_range(cal["harvest"]),
                soil_suitability_note=self._soil_suitability_note(crop, soil),
                has_market_data=has_market_data,
            ))

        # Sort by profit descending
        recommendations.sort(key=lambda r: r.expected_profit_per_ha, reverse=True)

        # Suppress crops with no market data in this state — their price is a national
        # fallback, making profit figures meaningless for local planning.
        no_data_crops = [r.crop_name for r in recommendations if not r.has_market_data]
        if no_data_crops:
            coverage_notes.append(
                f"{', '.join(no_data_crops)} excluded: no market price data recorded "
                f"in {state} mandis."
            )

        recommendations = [r for r in recommendations if r.has_market_data]

        # Also suppress crops where BOTH yield confidence is low AND price confidence is Red.
        def _is_unreliable(r: CropRecommendation) -> bool:
            return r.yield_confidence == "low" and r.price_confidence_colour == "Red"

        valid = [r for r in recommendations if not _is_unreliable(r)]
        suppressed_count = len(recommendations) - len(valid)
        if suppressed_count:
            coverage_notes.append(
                f"{suppressed_count} crop(s) hidden: insufficient data "
                "(low yield confidence and Red price confidence combined)."
            )

        # Fall back to all crops if every candidate was suppressed
        candidates = valid if valid else recommendations
        top5 = candidates[:5]
        for i, rec in enumerate(top5, start=1):
            rec.rank = i

        # Compute rainfall_deficit_pct from spi
        rainfall_deficit_pct = None
        if spi is not None:
            rainfall_deficit_pct = round(-spi * 20.0, 1)

        return HarvestAdvisorResponse(
            state=state,
            district=district,
            season=season,
            recommendations=top5,
            weather_warnings=warnings,
            rainfall_deficit_pct=rainfall_deficit_pct,
            drought_risk=drought_risk,
            soil_data_available=soil_df is not None,
            yield_data_available=yield_df is not None,
            forecast_available=forecast_available,
            disclaimer=DISCLAIMER,
            generated_at=datetime.now(timezone.utc).isoformat(),
            coverage_notes=coverage_notes,
        )

    def get_weather_warnings(self, state: str, district: str) -> list[WeatherWarning]:
        """Get weather warnings only (no crop recommendations)."""
        rainfall_df = _load_parquet_safe(
            DATA_DIR / "ranifall_data" / "combined" / "rainfall_district_monthly.parquet"
        )
        weather_csv_df = _load_csv_safe(
            DATA_DIR / "weather data" / "india_weather_daily_10years.csv"
        )
        warnings, _, _ = generate_all_warnings(
            district, state, self.db, rainfall_df, weather_csv_df
        )
        return warnings

    def get_districts_with_data(self, state: str) -> list[str]:
        """Return districts with at least soil or price data for a state."""
        districts: set[str] = set()

        soil_df = _load_parquet_safe(
            DATA_DIR / "soil-health" / "district_soil_aggregated.parquet"
        )
        if soil_df is not None:
            state_mask = soil_df["state"].str.lower() == state.lower()
            districts.update(soil_df[state_mask]["district"].str.title().tolist())

        rainfall_df = _load_parquet_safe(
            DATA_DIR / "ranifall_data" / "combined" / "rainfall_district_monthly.parquet"
        )
        if rainfall_df is not None:
            state_mask = rainfall_df["STATE"].str.lower() == state.lower()
            districts.update(rainfall_df[state_mask]["DISTRICT"].str.title().tolist())

        return sorted(districts)
