"""Shared feature engineering for directional price advisories."""
from __future__ import annotations

import re
from typing import Sequence

import numpy as np
import pandas as pd


DEFAULT_LAGS: tuple[int, ...] = (1, 3, 7, 14, 30)
DEFAULT_ROLL_WINDOWS: tuple[int, ...] = (7, 14, 30)
LATEST_REQUIRED_COLUMNS: tuple[str, ...] = (
    "lag_1",
    "lag_7",
    "lag_30",
    "rolling_mean_7",
    "rolling_std_30",
)
_NON_FEATURE_COLUMNS = frozenset(
    {
        "price_date",
        "district",
        "target_label",
        "future_price",
        "future_return",
        "future_return_pct",
        "target_date",
    }
)


def slugify(value: str) -> str:
    """Return a filesystem-safe lowercase slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    return slug.strip("_")


def district_feature_name(district: str) -> str:
    """Return the one-hot feature name for a district."""
    return f"district__{slugify(district)}"


def prepare_price_history(
    raw_df: pd.DataFrame,
    date_col: str = "price_date",
    district_col: str = "district",
    price_col: str = "modal_price",
    max_ffill_days: int = 3,
) -> pd.DataFrame:
    """Normalize raw district price rows into a daily district series."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["price_date", "district", "modal_price"])

    df = raw_df[[date_col, district_col, price_col]].copy()
    df = df.rename(
        columns={
            date_col: "price_date",
            district_col: "district",
            price_col: "modal_price",
        }
    )
    df = df.dropna(subset=["price_date", "district", "modal_price"])
    if df.empty:
        return pd.DataFrame(columns=["price_date", "district", "modal_price"])

    df["price_date"] = pd.to_datetime(df["price_date"])
    df["district"] = df["district"].astype(str).str.strip()
    df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
    df = df.dropna(subset=["modal_price"])
    df = df[df["modal_price"] > 0]
    if df.empty:
        return pd.DataFrame(columns=["price_date", "district", "modal_price"])

    grouped = (
        df.groupby(["district", "price_date"], as_index=False)["modal_price"]
        .mean()
        .sort_values(["district", "price_date"])
    )

    dense_frames: list[pd.DataFrame] = []
    for district, district_df in grouped.groupby("district", sort=False):
        series = district_df.set_index("price_date")["modal_price"].sort_index()
        full_index = pd.date_range(series.index.min(), series.index.max(), freq="D")
        dense = series.reindex(full_index).ffill(limit=max_ffill_days)
        dense = dense.dropna()
        if dense.empty:
            continue
        dense_frames.append(
            pd.DataFrame(
                {
                    "price_date": full_index,
                    "district": district,
                    "modal_price": dense.values.astype("float32"),
                }
            ).dropna(subset=["modal_price"])
        )

    if not dense_frames:
        return pd.DataFrame(columns=["price_date", "district", "modal_price"])

    result = pd.concat(dense_frames, ignore_index=True)
    return result.sort_values(["district", "price_date"]).reset_index(drop=True)


def build_feature_frame(
    history_df: pd.DataFrame,
    lags: Sequence[int] = DEFAULT_LAGS,
    roll_windows: Sequence[int] = DEFAULT_ROLL_WINDOWS,
) -> pd.DataFrame:
    """Build past-only directional features for each district-day row."""
    if history_df is None or history_df.empty:
        return pd.DataFrame(columns=["price_date", "district", "modal_price"])

    df = history_df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df = df.sort_values(["district", "price_date"]).reset_index(drop=True)

    feature_frames: list[pd.DataFrame] = []
    for _, district_df in df.groupby("district", sort=False):
        local = district_df.copy()
        price = local["modal_price"].astype("float32")

        local["history_index"] = np.arange(len(local), dtype="float32")

        for lag in lags:
            lagged = price.shift(lag)
            local[f"lag_{lag}"] = lagged
            local[f"return_{lag}"] = (price / lagged) - 1.0

        prev_price = price.shift(1)
        prev_return = prev_price.pct_change()
        for window in roll_windows:
            rolling_mean = prev_price.rolling(window=window, min_periods=window).mean()
            rolling_std = prev_price.rolling(window=window, min_periods=window).std()
            local[f"rolling_mean_{window}"] = rolling_mean
            local[f"rolling_std_{window}"] = rolling_std
            local[f"gap_to_mean_{window}"] = (price / rolling_mean) - 1.0
            local[f"volatility_{window}"] = prev_return.rolling(
                window=window,
                min_periods=window,
            ).std()

        day_of_year = local["price_date"].dt.dayofyear.astype("float32")
        day_of_week = local["price_date"].dt.dayofweek.astype("float32")
        month = local["price_date"].dt.month.astype("float32")

        local["sin_annual"] = np.sin(2.0 * np.pi * day_of_year / 365.25)
        local["cos_annual"] = np.cos(2.0 * np.pi * day_of_year / 365.25)
        local["sin_weekly"] = np.sin(2.0 * np.pi * day_of_week / 7.0)
        local["cos_weekly"] = np.cos(2.0 * np.pi * day_of_week / 7.0)
        local["sin_monthly"] = np.sin(2.0 * np.pi * month / 12.0)
        local["cos_monthly"] = np.cos(2.0 * np.pi * month / 12.0)

        local["recent_7d_change_pct"] = ((price / price.shift(7)) - 1.0) * 100.0
        local["recent_30d_change_pct"] = ((price / price.shift(30)) - 1.0) * 100.0

        feature_frames.append(local)

    feature_df = pd.concat(feature_frames, ignore_index=True)
    feature_df = feature_df.replace([np.inf, -np.inf], np.nan)
    return feature_df.sort_values(["district", "price_date"]).reset_index(drop=True)


def attach_direction_labels(
    feature_df: pd.DataFrame,
    horizon_days: int = 7,
    move_threshold: float = 0.05,
) -> pd.DataFrame:
    """Attach future-direction labels to a feature frame."""
    if feature_df is None or feature_df.empty:
        return pd.DataFrame(columns=["price_date", "district", "modal_price", "target_label"])

    labeled_frames: list[pd.DataFrame] = []
    for _, district_df in feature_df.groupby("district", sort=False):
        local = district_df.copy()
        future_price = local["modal_price"].shift(-horizon_days)
        future_return = (future_price / local["modal_price"]) - 1.0
        local["future_price"] = future_price
        local["future_return"] = future_return
        local["future_return_pct"] = future_return * 100.0
        local["target_date"] = local["price_date"] + pd.to_timedelta(horizon_days, unit="D")
        local["target_label"] = np.where(
            future_return >= move_threshold,
            "up",
            np.where(future_return <= -move_threshold, "down", "flat"),
        )
        labeled_frames.append(local)

    labeled = pd.concat(labeled_frames, ignore_index=True)
    labeled = labeled.dropna(subset=["future_price", "target_label"])
    return labeled.reset_index(drop=True)


def filter_complete_feature_rows(feature_df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows that have the full feature set available."""
    if feature_df is None or feature_df.empty:
        columns = list(feature_df.columns) if feature_df is not None else []
        return pd.DataFrame(columns=columns)

    feature_cols = [c for c in feature_df.columns if c not in _NON_FEATURE_COLUMNS]
    if not feature_cols:
        return feature_df.copy()

    complete = feature_df.dropna(subset=feature_cols)
    complete = complete.replace([np.inf, -np.inf], np.nan).dropna(subset=feature_cols)
    return complete.sort_values(["district", "price_date"]).reset_index(drop=True)


def select_latest_feature_row(feature_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest fully-populated feature row for inference."""
    if feature_df is None or feature_df.empty:
        columns = list(feature_df.columns) if feature_df is not None else []
        return pd.DataFrame(columns=columns)

    required = [c for c in LATEST_REQUIRED_COLUMNS if c in feature_df.columns]
    if not required:
        return pd.DataFrame(columns=feature_df.columns)

    latest = (
        feature_df.replace([np.inf, -np.inf], np.nan)
        .dropna(subset=required)
        .sort_values("price_date")
        .tail(1)
    )
    return latest.reset_index(drop=True)


def vectorize_features(
    feature_df: pd.DataFrame,
    feature_columns: Sequence[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Turn a feature frame into a model matrix with stable district dummies."""
    if feature_df is None or feature_df.empty:
        columns = list(feature_columns) if feature_columns is not None else []
        return pd.DataFrame(columns=columns), columns

    numeric_cols = [c for c in feature_df.columns if c not in _NON_FEATURE_COLUMNS]
    numeric_frame = feature_df[numeric_cols].astype("float32").copy()

    district_slugs = feature_df["district"].astype(str).map(district_feature_name)
    district_dummies = pd.get_dummies(district_slugs, dtype="float32")
    district_dummies.index = feature_df.index

    matrix = pd.concat([numeric_frame, district_dummies], axis=1)
    matrix = matrix.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    if feature_columns is not None:
        aligned = matrix.reindex(columns=list(feature_columns), fill_value=0.0)
        return aligned, list(feature_columns)

    return matrix, list(matrix.columns)
