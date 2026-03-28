"""Weather warning generation from historical SPI and heat stress signals."""
from __future__ import annotations
import logging
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.harvest_advisor.schemas import WeatherWarning
from app.harvest_advisor.weather_client import OpenMeteoClient

logger = logging.getLogger(__name__)


def compute_spi_3month(
    rainfall_df: pd.DataFrame, district: str
) -> tuple[Optional[float], Optional[str]]:
    """
    Compute 3-month SPI for a district using last 3 months of data.

    Returns (spi_value, affected_period_str) or (None, None) if insufficient data.

    SPI < -1.5 -> DROUGHT severe; < -1.0 -> DROUGHT moderate
    SPI > +1.5 -> FLOOD; > +1.0 -> EXCESS RAIN
    """
    dist_data = rainfall_df[
        rainfall_df["DISTRICT"].str.lower() == district.lower()
    ].copy()
    if dist_data.empty:
        return None, None

    # Create date column for sorting
    dist_data["date"] = pd.to_datetime(
        dist_data["year"].astype(str)
        + "-"
        + dist_data["month"].astype(str).str.zfill(2)
        + "-01"
    )
    dist_data = dist_data.sort_values("date")

    if len(dist_data) < 36:  # Need at least 3 years for meaningful SPI
        return None, None

    # Get last 3 months of available data
    recent = dist_data.tail(3)
    recent_sum = recent["rainfall"].sum()

    # Baseline: compute mean and std of 3-month running sums
    rainfall_vals = dist_data["rainfall"].values
    baseline_3m = []
    for i in range(3, len(rainfall_vals) - 3):
        baseline_3m.append(sum(rainfall_vals[i : i + 3]))

    if not baseline_3m:
        return None, None

    mean_3m = np.mean(baseline_3m)
    std_3m = np.std(baseline_3m)

    if std_3m < 1e-6:
        return 0.0, None

    spi = (recent_sum - mean_3m) / std_3m

    # Format affected period
    last_row = recent.iloc[-1]
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    period = f"{month_names[int(last_row['month']) - 1]} {int(last_row['year'])}"

    return float(spi), period


def generate_spi_warnings(
    spi: float, period: str, district: str
) -> list[WeatherWarning]:
    """Convert SPI value to WeatherWarning objects."""
    warnings: list[WeatherWarning] = []
    if spi < -1.5:
        warnings.append(WeatherWarning(
            warning_type="drought",
            severity="high",
            message=f"Severe drought conditions in {district}. 3-month SPI = {spi:.2f}.",
            source="historical",
            affected_period=period,
            crop_impact="Avoid water-intensive crops. Prefer drought-tolerant varieties (bajra, jowar, groundnut).",
        ))
    elif spi < -1.0:
        warnings.append(WeatherWarning(
            warning_type="drought",
            severity="medium",
            message=f"Moderate drought conditions in {district}. 3-month SPI = {spi:.2f}.",
            source="historical",
            affected_period=period,
            crop_impact="Ensure irrigation availability. Monitor soil moisture closely.",
        ))
    elif spi > 1.5:
        warnings.append(WeatherWarning(
            warning_type="flood",
            severity="high",
            message=f"Excess rainfall in {district}. 3-month SPI = {spi:.2f}.",
            source="historical",
            affected_period=period,
            crop_impact="Risk of waterlogging. Avoid low-lying fields. Prefer raised-bed cultivation.",
        ))
    elif spi > 1.0:
        warnings.append(WeatherWarning(
            warning_type="excess_rain",
            severity="low",
            message=f"Above-normal rainfall in {district}. 3-month SPI = {spi:.2f}.",
            source="historical",
            affected_period=period,
            crop_impact="Ensure good field drainage. Watch for fungal diseases.",
        ))
    return warnings


def generate_heat_warnings(
    weather_df: pd.DataFrame, district: str
) -> list[WeatherWarning]:
    """Generate heat stress warnings from recent weather data."""
    warnings: list[WeatherWarning] = []
    dist_data = weather_df[weather_df["district"].str.lower() == district.lower()]
    if dist_data.empty:
        return warnings

    # Use last 90 days
    recent = dist_data.tail(90)
    if "avg_temp_c" not in recent.columns:
        return warnings

    max_temp = recent["avg_temp_c"].max()
    if pd.isna(max_temp):
        return warnings

    if max_temp > 40:
        warnings.append(WeatherWarning(
            warning_type="heat_stress",
            severity="extreme",
            message=f"Extreme heat in {district}. Peak avg temp {max_temp:.1f}\u00b0C in recent period.",
            source="historical",
            affected_period="Recent 90 days",
            crop_impact="Avoid sowing heat-sensitive crops. Use shade nets and increase irrigation frequency.",
        ))
    elif max_temp > 35:
        warnings.append(WeatherWarning(
            warning_type="heat_stress",
            severity="medium",
            message=f"Heat stress risk in {district}. Peak avg temp {max_temp:.1f}\u00b0C in recent period.",
            source="historical",
            affected_period="Recent 90 days",
            crop_impact="Select heat-tolerant varieties. Schedule field operations in cooler hours.",
        ))
    return warnings


def generate_all_warnings(
    district: str,
    state: str,
    db: Session,
    rainfall_df: Optional[pd.DataFrame] = None,
    weather_df: Optional[pd.DataFrame] = None,
) -> tuple[list[WeatherWarning], Optional[float], str]:
    """
    Generate all weather warnings for a district.

    Returns (warnings, spi_value, drought_risk)
    drought_risk: "none"|"low"|"medium"|"high"|"extreme"
    """
    all_warnings: list[WeatherWarning] = []
    spi_value = None
    drought_risk = "none"

    # SPI from rainfall data
    if rainfall_df is not None and not rainfall_df.empty:
        spi, period = compute_spi_3month(rainfall_df, district)
        if spi is not None and period is not None:
            spi_value = spi
            spi_warnings = generate_spi_warnings(spi, period, district)
            all_warnings.extend(spi_warnings)
            if spi < -1.5:
                drought_risk = "high"
            elif spi < -1.0:
                drought_risk = "medium"
            else:
                drought_risk = "none"

    # Heat stress from weather data
    if weather_df is not None and not weather_df.empty:
        heat_warnings = generate_heat_warnings(weather_df, district)
        all_warnings.extend(heat_warnings)

    # Live forecast from Open-Meteo (best effort)
    try:
        client = OpenMeteoClient()
        forecast = client.fetch_forecast(district, state, db)
        if forecast and "daily" in forecast:
            daily = forecast["daily"]
            temps = daily.get("temperature_2m_max", [])
            precip = daily.get("precipitation_sum", [])
            if temps:
                valid_temps = [t for t in temps if t is not None]
                if valid_temps:
                    peak_temp = max(valid_temps)
                    if peak_temp > 40:
                        all_warnings.append(WeatherWarning(
                            warning_type="heat_stress",
                            severity="extreme",
                            message=f"16-day forecast shows extreme heat ({peak_temp:.1f}\u00b0C) in {district}.",
                            source="forecast",
                            affected_period="Next 16 days",
                            crop_impact="Delay sowing if possible. Ensure adequate irrigation.",
                        ))
                    elif peak_temp > 38:
                        all_warnings.append(WeatherWarning(
                            warning_type="heat_stress",
                            severity="medium",
                            message=f"16-day forecast shows heat stress ({peak_temp:.1f}\u00b0C) in {district}.",
                            source="forecast",
                            affected_period="Next 16 days",
                            crop_impact="Monitor crops closely. Increase watering frequency.",
                        ))
            if precip:
                total_precip = sum(p for p in precip if p is not None)
                if total_precip > 200:
                    all_warnings.append(WeatherWarning(
                        warning_type="excess_rain",
                        severity="medium",
                        message=f"16-day forecast: {total_precip:.0f}mm expected in {district}.",
                        source="forecast",
                        affected_period="Next 16 days",
                        crop_impact="Prepare drainage. Watch for soil erosion and waterlogging.",
                    ))
    except Exception as e:
        logger.debug(f"Live forecast unavailable for {district}: {e}")

    return all_warnings, spi_value, drought_risk
