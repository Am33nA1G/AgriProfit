"""
Price feature engineering — lag and rolling statistics with strict cutoff_date enforcement.

CRITICAL IMPLEMENTATION NOTES:
1. Price series is IRREGULAR (market trading days, gaps up to 32 calendar days).
   pandas.shift(n) shifts by N records, not N calendar days.
   Must reindex to daily calendar BEFORE computing lags.

2. cutoff_date is enforced INSIDE this function via series.loc[:cutoff_date].
   The caller MUST NOT be relied upon for cutoff enforcement.

3. Forward-fill ONLY during daily reindex — never backfill.
   Backfill would introduce future prices into past dates.

4. Roll windows computed on series.shift(1) — excludes current-day price from its own window.
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np


def compute_price_features(
    series: pd.Series,
    cutoff_date: pd.Timestamp,
    lags: list[int] = None,
    roll_windows: list[int] = None,
) -> pd.DataFrame:
    """
    Compute lag and rolling statistics for a commodity-district price series.

    Args:
        series: pd.Series with DatetimeIndex, values are modal prices.
                Irregular frequency (market trading days only) is expected.
        cutoff_date: Maximum date to include. Enforced INSIDE this function.
                     All data after cutoff_date is excluded structurally.
        lags: Calendar-day lags to compute. Default: [7, 14, 30, 90].
        roll_windows: Rolling window sizes in calendar days. Default: [7, 30].

    Returns:
        pd.DataFrame with DatetimeIndex (daily frequency), columns:
            price_modal: original price (forward-filled to daily)
            price_lag_{n}d: price n calendar days ago
            price_roll_mean_{n}d: rolling mean over n calendar days (excludes current day)
            price_roll_std_{n}d: rolling std over n calendar days (excludes current day)
        Returns empty DataFrame if series is empty after cutoff enforcement.
    """
    if lags is None:
        lags = [7, 14, 30, 90]
    if roll_windows is None:
        roll_windows = [7, 30]

    # STEP 1: Enforce cutoff structurally
    s = series.loc[:cutoff_date].copy()
    if s.empty:
        return pd.DataFrame()

    # STEP 2: Reindex to daily calendar — required for correct calendar-day lags
    daily_index = pd.date_range(s.index.min(), s.index.max(), freq="D")
    s_daily = s.reindex(daily_index)

    # STEP 3: Forward-fill only (never backfill — backfill = future data)
    s_daily = s_daily.ffill()

    result = pd.DataFrame(index=daily_index)
    result["price_modal"] = s_daily.values

    # STEP 4: Lag features — shift by calendar days after daily reindex
    for lag in lags:
        result[f"price_lag_{lag}d"] = s_daily.shift(lag).values

    # STEP 5: Rolling stats on shifted series (excludes current-day price from window)
    s_shifted = s_daily.shift(1)
    for window in roll_windows:
        rolled = s_shifted.rolling(window=window, min_periods=1)
        result[f"price_roll_mean_{window}d"] = rolled.mean().values
        result[f"price_roll_std_{window}d"] = rolled.std().values

    return result
