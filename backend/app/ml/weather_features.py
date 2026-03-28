"""
Weather feature engineering — Tier A+ / Tier B split with NaN passthrough.

FEAT-03 requirement: Tier B districts (~310) receive absent features (empty DataFrame),
NOT imputed values. XGBoost handles NaN natively. Imputing creates false signal.

Tier classification:
  Tier A+ (~261): Districts with harmonised weather coverage
                  (in district_name_map WHERE source_dataset='weather' AND match_type IN ('exact','fuzzy_accepted'))
  Tier B  (~310): All other price districts — no weather data, empty DataFrame returned

The tier_a_plus_districts set MUST be built by the caller (one DB query outside this function).
This function is pure — no database calls inside.
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd


WEATHER_FEATURE_COLS = ["max_temp_c", "min_temp_c", "avg_temp_c", "avg_humidity", "max_wind_kph"]


def compute_weather_features(
    weather_df: pd.DataFrame,
    canonical_district: str,
    cutoff_date: pd.Timestamp,
    tier_a_plus_districts: set,
) -> pd.DataFrame:
    """
    Return daily weather features for a district, or empty DataFrame if Tier B.

    Args:
        weather_df: columns [date, district, max_temp_c, min_temp_c, avg_temp_c, avg_humidity, max_wind_kph]
                    district column contains CANONICAL district names (pre-mapped via district_name_map).
        canonical_district: The canonical district name (from price dataset).
        cutoff_date: Maximum date — data after this is excluded structurally.
        tier_a_plus_districts: Set of canonical districts with validated weather coverage.
                                Build once via DB query; pass as parameter here.

    Returns:
        pd.DataFrame with DatetimeIndex, columns = WEATHER_FEATURE_COLS.
        Empty (0 rows) for Tier B districts. Present values for Tier A+.
        Never imputes — absent means absent.
    """
    if canonical_district not in tier_a_plus_districts:
        # Tier B: return empty frame — caller knows to treat as NaN features
        return pd.DataFrame(columns=WEATHER_FEATURE_COLS)

    district_data = weather_df[
        (weather_df["district"] == canonical_district)
        & (pd.to_datetime(weather_df["date"]) <= cutoff_date)
    ].copy()

    if district_data.empty:
        return pd.DataFrame(columns=WEATHER_FEATURE_COLS)

    district_data["date"] = pd.to_datetime(district_data["date"])
    district_data = district_data.set_index("date").sort_index()

    return district_data[WEATHER_FEATURE_COLS]
