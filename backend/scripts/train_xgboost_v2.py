"""
XGBoost v2 training — extended lags (7/14/30/90), 90-day horizon, weather exogenous.

Only overwrites v1 if new MAPE <= old MAPE * 1.05 or no v1 exists.

Usage:
    cd backend
    python -m scripts.train_xgboost_v2
    python -m scripts.train_xgboost_v2 --dry-run
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import gc
import json
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    from skforecast.exceptions import MissingValuesWarning, InputTypeWarning
    warnings.filterwarnings("ignore", category=MissingValuesWarning)
    warnings.filterwarnings("ignore", category=InputTypeWarning)
except ImportError:
    pass

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from decimal import Decimal
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MIN_DAYS_TRAIN = 730
LAGS = [7, 14, 30, 90]
HORIZON = 90


def load_weather_exog() -> Optional[pd.DataFrame]:
    """Load monthly weather features and expand to daily for exogenous input."""
    weather_path = REPO_ROOT / "data" / "features" / "weather_monthly_features.parquet"
    if not weather_path.exists():
        print("  Weather features not found, training without exogenous variables")
        return None

    wdf = pd.read_parquet(weather_path, engine="pyarrow")
    # Keep only numeric weather features
    keep_cols = ["district", "year", "month", "avg_temp_c", "avg_humidity",
                 "rainfall_mm", "rainfall_deviation_pct"]
    wdf = wdf[[c for c in keep_cols if c in wdf.columns]].copy()
    return wdf


def build_series_df(
    raw_df: pd.DataFrame,
    min_days: int = MIN_DAYS_TRAIN,
) -> tuple[pd.DataFrame, list[dict]]:
    """Build wide-format series DataFrame from raw price data."""
    df = raw_df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df["modal_price"] = df["modal_price"].astype("float32")

    MAX_DISTRICTS = 30
    district_counts = df.groupby("district").size().sort_values(ascending=False)
    top_districts = district_counts.head(MAX_DISTRICTS).index
    df = df[df["district"].isin(top_districts)]

    wide = df.pivot_table(
        index="price_date", columns="district", values="modal_price", aggfunc="mean",
    )
    wide.index = pd.DatetimeIndex(wide.index)
    wide = wide.sort_index()

    full_range = pd.date_range(start=wide.index.min(), end=wide.index.max(), freq="D")
    wide = wide.reindex(full_range)
    wide.index.name = "price_date"
    wide.index.freq = "D"

    wide = wide.ffill(limit=7)
    wide = wide.interpolate(method="linear", limit=14, limit_direction="forward")

    MAX_LAG = max(LAGS)
    excluded = []
    keep_cols = []
    for col in wide.columns:
        col_data = wide[col].dropna()
        if len(col_data) == 0:
            excluded.append({"district": col, "reason": "no_data"})
            continue
        span_days = (col_data.index.max() - col_data.index.min()).days
        if span_days < min_days:
            excluded.append({"district": col, "reason": "insufficient_data"})
            continue
        tail = wide[col].iloc[-MAX_LAG:]
        fill_ratio = tail.notna().sum() / len(tail)
        if fill_ratio < 0.8:
            excluded.append({"district": col, "reason": "sparse_recent_data"})
            continue
        keep_cols.append(col)

    series_df = wide[keep_cols]
    for col in series_df.columns:
        if series_df[col].isna().any():
            series_df[col] = series_df[col].fillna(series_df[col].median())

    return series_df, excluded


def build_exog_for_series(
    series_df: pd.DataFrame,
    weather_df: Optional[pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """Build exogenous feature DataFrame matching the series index.

    Maps each district column to weather features via district name matching.
    Returns None if weather data is unavailable or doesn't match.
    """
    if weather_df is None:
        return None

    weather_df = weather_df.copy()
    weather_df["district_lower"] = weather_df["district"].str.strip().str.lower()

    exog_frames = []
    for district_col in series_df.columns:
        district_lower = district_col.strip().lower()
        dist_weather = weather_df[weather_df["district_lower"] == district_lower]
        if dist_weather.empty:
            return None  # Can't build consistent exog, skip

        # Create daily index from monthly weather
        daily_records = []
        for _, row in dist_weather.iterrows():
            year, month = int(row["year"]), int(row["month"])
            start = pd.Timestamp(year=year, month=month, day=1)
            end = start + pd.offsets.MonthEnd(0)
            days = pd.date_range(start, end, freq="D")
            for day in days:
                rec = {"price_date": day, "level_skforecast": district_col}
                for feat in ["avg_temp_c", "avg_humidity", "rainfall_mm", "rainfall_deviation_pct"]:
                    if feat in row.index:
                        rec[feat] = row[feat]
                daily_records.append(rec)

        exog_frames.append(pd.DataFrame(daily_records))

    if not exog_frames:
        return None

    exog = pd.concat(exog_frames, ignore_index=True)
    exog["price_date"] = pd.to_datetime(exog["price_date"])
    exog = exog.set_index(["level_skforecast", "price_date"])

    # Filter to only dates in our series
    valid_dates = series_df.index
    exog = exog[exog.index.get_level_values("price_date").isin(valid_dates)]

    if exog.empty:
        return None

    return exog


def get_v1_mape(slug: str) -> Optional[float]:
    """Check if v1 model exists and return its MAPE (from training log)."""
    v1_path = ARTIFACTS_DIR / f"{slug}.joblib"
    if not v1_path.exists():
        return None
    try:
        v1 = joblib.load(v1_path)
        if hasattr(v1, "mape_mean_"):
            return float(v1.mape_mean_)
    except Exception:
        pass
    return None


def train_commodity_v2(
    commodity: str,
    series_df: pd.DataFrame,
    excluded: list[dict],
    weather_df: Optional[pd.DataFrame],
    db,
    dry_run: bool = False,
) -> None:
    """Train v2 model for one commodity."""
    from skforecast.recursive import ForecasterRecursiveMultiSeries
    from skforecast.model_selection import backtesting_forecaster_multiseries, TimeSeriesFold
    from xgboost import XGBRegressor

    forecaster = ForecasterRecursiveMultiSeries(
        regressor=XGBRegressor(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.08,
            tree_method="hist",
            random_state=42,
        ),
        lags=LAGS,
        encoding="ordinal",
        transformer_series=None,
        dropna_from_series=True,
    )

    cv = TimeSeriesFold(
        steps=HORIZON,
        initial_train_size=int(len(series_df) * 0.7),
        refit=False,
        fixed_train_size=False,
    )

    # Build exogenous features
    exog = build_exog_for_series(series_df, weather_df)

    fit_kwargs = {"series": series_df}
    bt_kwargs = {
        "forecaster": forecaster,
        "series": series_df,
        "cv": cv,
        "metric": ["mean_squared_error", "mean_absolute_percentage_error"],
        "n_jobs": 1,
    }
    if exog is not None:
        fit_kwargs["exog"] = exog
        bt_kwargs["exog"] = exog

    metrics_df, _ = backtesting_forecaster_multiseries(**bt_kwargs)

    rmse_arr = np.sqrt(metrics_df["mean_squared_error"].values)
    mape_arr = metrics_df["mean_absolute_percentage_error"].values
    new_mape = float(mape_arr.mean())

    slug = commodity.lower().replace(" ", "_").replace("/", "_")

    # Check v1 MAPE gate
    v1_mape = get_v1_mape(slug)
    if v1_mape is not None and new_mape > v1_mape * 1.05:
        print(
            f"  [SKIP SAVE] v2 MAPE={new_mape:.4f} > v1 MAPE={v1_mape:.4f} * 1.05. "
            f"Not saving v2."
        )
        return

    if dry_run:
        print(
            f"  [DRY RUN] {commodity}: RMSE={rmse_arr.mean():.2f} MAPE={new_mape:.4f}"
        )
        return

    # Fit on all data and save as v2
    forecaster.fit(**fit_kwargs)
    artifact_path = ARTIFACTS_DIR / f"{slug}_v2.joblib"
    joblib.dump(forecaster, str(artifact_path))
    print(
        f"  [OK] {commodity}: RMSE={rmse_arr.mean():.2f} "
        f"MAPE={new_mape:.4f} -> {artifact_path.name}"
    )


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost v2 models")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't save models")
    args = parser.parse_args()

    from sqlalchemy.orm import Session
    from app.database.session import SessionLocal
    from app.models.price_history import PriceHistory
    from app.models.commodity import Commodity
    from app.models.mandi import Mandi
    from sqlalchemy import select
    from datetime import datetime, timedelta

    TRAIN_LOOKBACK_DAYS = 1825
    date_cutoff = (datetime.now() - timedelta(days=TRAIN_LOOKBACK_DAYS)).date()

    weather_df = load_weather_exog()

    db = SessionLocal()
    try:
        commodities = db.execute(
            select(Commodity.id, Commodity.name)
            .join(PriceHistory, PriceHistory.commodity_id == Commodity.id)
            .distinct()
            .order_by(Commodity.name)
        ).all()

        n = len(commodities)
        print(f"Found {n} commodities to process")

        for i, (commodity_id, commodity_name) in enumerate(commodities, 1):
            slug = commodity_name.lower().replace(" ", "_").replace("/", "_")
            v2_artifact = ARTIFACTS_DIR / f"{slug}_v2.joblib"
            if v2_artifact.exists():
                print(f"\n--- Skipping: {commodity_name} (v2 already trained) ---")
                continue

            print(f"\nTraining {commodity_name} ({i}/{n})...")

            result = db.execute(
                select(
                    PriceHistory.price_date,
                    Mandi.district,
                    PriceHistory.modal_price,
                )
                .join(Mandi, PriceHistory.mandi_id == Mandi.id)
                .where(PriceHistory.commodity_id == commodity_id)
                .where(PriceHistory.price_date >= date_cutoff)
            ).all()

            if not result:
                print(f"  [SKIP] No price data with linked mandi")
                continue

            raw_df = pd.DataFrame(result, columns=["price_date", "district", "modal_price"])
            print(f"  {len(raw_df):,} rows, {raw_df['district'].nunique()} districts")
            series_df, excluded = build_series_df(raw_df, min_days=MIN_DAYS_TRAIN)

            if len(series_df.columns) < 2:
                print(f"  [SKIP] Only {len(series_df.columns)} qualifying district(s)")
                continue

            try:
                train_commodity_v2(
                    commodity_name, series_df, excluded, weather_df, db,
                    dry_run=args.dry_run,
                )
            except Exception as e:
                print(f"  [ERROR] {commodity_name}: {e}")
            finally:
                raw_df = series_df = excluded = result = None
                gc.collect()

    finally:
        db.close()


if __name__ == "__main__":
    main()
