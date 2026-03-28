"""
serving_exog.py — Future-date exogenous feature builder for ML forecast serving.

Strategy (Phase 2 / 4.7):
  - Days 1–16:  Open Meteo 16-day forecast (if available)
  - Days 17+:   Climatological normals computed from weather_monthly_features.parquet
  - Always:     Fourier deterministic features

The SAME feature columns produced here must match what was stored at training time
in meta["exog_columns"]. The caller in service.py should reindex to that schema.

Call `load_climatological_normals()` once at app startup (lifespan) before any
forecast requests are served.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ── Module-level normal lookup ─────────────────────────────────────────────────
# Populated by load_climatological_normals() at startup.
# Format: {month_int: {temp: float, humidity: float, rainfall: float}}
_CLIMATOLOGICAL_NORMALS: dict[int, dict] = {}

# Repo root: this file is at backend/app/ml/serving_exog.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _build_normals_from_parquet(parquet_path: Path) -> dict[int, dict]:
    """Compute monthly climate averages — used as deterministic future exog."""
    wdf = pd.read_parquet(parquet_path, engine="pyarrow")

    agg_cols = {
        col: "mean"
        for col in ["avg_temp_c", "avg_humidity", "rainfall_mm"]
        if col in wdf.columns
    }
    if not agg_cols:
        return {}

    group_col = "month" if "month" in wdf.columns else None
    if group_col is None:
        return {}

    monthly = wdf.groupby(group_col).agg(agg_cols)

    normals: dict[int, dict] = {}
    for month, row in monthly.iterrows():
        normals[int(month)] = {
            "temp":     round(float(row.get("avg_temp_c", 25.0)), 2),
            "humidity": round(float(row.get("avg_humidity", 70.0)), 2),
            "rainfall": round(float(row.get("rainfall_mm", 0.0)), 2),
        }
    return normals


def load_climatological_normals() -> None:
    """
    Build and cache climatological normals from weather_monthly_features.parquet.
    Call once at app startup via the FastAPI lifespan handler.
    Silently no-ops if the parquet file is missing.
    """
    global _CLIMATOLOGICAL_NORMALS
    weather_path = _REPO_ROOT / "data" / "features" / "weather_monthly_features.parquet"
    if not weather_path.exists():
        return

    try:
        _CLIMATOLOGICAL_NORMALS = _build_normals_from_parquet(weather_path)
    except Exception:
        # Non-fatal: serving continues with default constants
        _CLIMATOLOGICAL_NORMALS = {}


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


def build_future_exog(
    start_date,
    horizon: int,
    use_open_meteo: bool = True,
) -> pd.DataFrame:
    """
    Build exog DataFrame for future prediction dates.

    Days 1-16:  Open Meteo 16-day forecast (if available and use_open_meteo=True).
    Days 17+:   Climatological normals (deterministic, no API dependency).
    Always:     Fourier features appended.

    Args:
        start_date: First forecast date (date or Timestamp).
        horizon:    Number of forecast days.
        use_open_meteo: Try Open Meteo API for near-term weather.

    Returns:
        DataFrame with DatetimeIndex, columns matching training exog schema.
    """
    future_index = pd.date_range(start=start_date, periods=horizon, freq="D")
    fourier = _build_fourier_exog(future_index)

    # Attempt to fetch Open Meteo data for near-term horizon
    open_meteo_data: dict[pd.Timestamp, dict] = {}
    if use_open_meteo and _CLIMATOLOGICAL_NORMALS:
        try:
            from app.harvest_advisor.weather_client import fetch_forecast
            forecast = fetch_forecast(days=min(16, horizon))
            open_meteo_data = {
                pd.Timestamp(r["date"]): r
                for r in forecast.get("daily", [])
            }
        except Exception:
            pass  # Graceful: fall through to normals only

    # Build climate rows — Open Meteo for days 1-16, normals for the rest
    climate_rows = []
    for d in future_index:
        if d in open_meteo_data:
            row = open_meteo_data[d]
            climate_rows.append({
                "weather_temp":     float(row.get("temperature_2m_mean", 25.0)),
                "weather_humidity": float(row.get("relative_humidity_2m_mean", 70.0)),
                "weather_rainfall": float(row.get("precipitation_sum", 0.0)),
            })
        else:
            norm = _CLIMATOLOGICAL_NORMALS.get(
                d.month,
                {"temp": 25.0, "humidity": 70.0, "rainfall": 0.0},
            )
            climate_rows.append({
                "weather_temp":     norm["temp"],
                "weather_humidity": norm["humidity"],
                "weather_rainfall": norm["rainfall"],
            })

    if climate_rows:
        climate_df = pd.DataFrame(climate_rows, index=future_index)
        return pd.concat([fourier, climate_df], axis=1)

    # No climate data available — return Fourier only
    return fourier


def align_exog_to_training(
    future_exog: pd.DataFrame,
    train_exog_columns: list[str],
) -> pd.DataFrame:
    """
    Reindex future exog to exactly the columns used at training time.
    Missing columns filled with 0; extra columns dropped.
    This ensures the XGBoost model sees the same feature schema.
    """
    return future_exog.reindex(columns=train_exog_columns, fill_value=0.0)
