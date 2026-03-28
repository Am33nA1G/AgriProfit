"""
Shared feature builder for 7-day direct multi-step price forecasting.

Used by both the training script (backend/scripts/train_7day_model.py)
and the serving layer (backend/app/forecast/service_7d.py).

Design:
  - Direct multi-step: 7 separate targets (t+1 … t+7), no recursive error accumulation
  - Log1p-transformed prices: handles price level differences across commodities
  - Rolling stats use shift(1) to prevent any target leakage
  - Minimum 32 rows required to build lag-30 + some headroom
"""
import numpy as np
import pandas as pd

# Lag days to use as features
LAG_DAYS: list[int] = [1, 2, 3, 7, 14, 21, 30]

# Rolling windows (applied on lag-1-shifted series to avoid leakage)
ROLL_WINDOWS: list[int] = [7, 14, 30]

# Ordered list of all feature column names — MUST match between training and serving
FEATURE_COLS: list[str] = (
    [f"lag_{d}" for d in LAG_DAYS]
    + [f"roll_mean_{w}" for w in ROLL_WINDOWS]
    + [f"roll_std_{w}" for w in ROLL_WINDOWS]
    + ["day_of_week", "month", "day_of_year", "week_of_year", "district_enc"]
)

TARGET_COLS: list[str] = [f"target_h{h}" for h in range(1, 8)]
N_HORIZONS: int = 7
MIN_SERIES_ROWS: int = 37  # lag_30 + 7 target days


def build_features_from_series(
    series: pd.Series,
    district_enc: int,
) -> pd.DataFrame:
    """Build a feature + target dataframe from a single district's price time series.

    Args:
        series: pd.Series with DatetimeIndex, float price values (Rs/quintal).
                Should already be daily-aggregated (one price per date).
        district_enc: Integer label-encoded district ID.

    Returns:
        DataFrame with columns FEATURE_COLS + TARGET_COLS.
        Rows with any NaN in features or targets are dropped.
        Returns empty DataFrame if insufficient data.
    """
    if len(series) < MIN_SERIES_ROWS:
        return pd.DataFrame()

    df = pd.DataFrame({"price": series.values}, index=pd.to_datetime(series.index))
    df = df.sort_index()
    df["log_price"] = np.log1p(df["price"].clip(lower=0.0))

    # Lag features — all reference past values, no leakage
    for d in LAG_DAYS:
        df[f"lag_{d}"] = df["log_price"].shift(d)

    # Rolling stats on shift(1) — no leakage since we look back from yesterday
    rolled = df["log_price"].shift(1)
    for w in ROLL_WINDOWS:
        min_p = max(1, w // 2)
        df[f"roll_mean_{w}"] = rolled.rolling(w, min_periods=min_p).mean()
        df[f"roll_std_{w}"] = rolled.rolling(w, min_periods=min_p).std().fillna(0.0)

    # Calendar features
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month
    df["day_of_year"] = df.index.day_of_year
    df["week_of_year"] = df.index.isocalendar().week.astype(int)

    # District encoding
    df["district_enc"] = int(district_enc)

    # Direct multi-step targets — future log-prices, no leakage
    for h in range(1, N_HORIZONS + 1):
        df[f"target_h{h}"] = df["log_price"].shift(-h)

    return df.dropna(subset=FEATURE_COLS + TARGET_COLS)


def build_serving_vector(
    series: pd.Series,
    district_enc: int,
) -> np.ndarray | None:
    """Build a single 1-D feature vector for live inference.

    Uses the most recent date available in series.

    Args:
        series: pd.Series with DatetimeIndex, at least 32 rows of daily prices.
        district_enc: Integer label-encoded district ID.

    Returns:
        1-D float64 array of shape (len(FEATURE_COLS),), or None if insufficient data.
    """
    df = build_features_from_series(series, district_enc)
    if df.empty:
        return None

    row = df.iloc[-1][FEATURE_COLS]
    if row.isna().any():
        return None

    return row.values.astype(np.float64)
