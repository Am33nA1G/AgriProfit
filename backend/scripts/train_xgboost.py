"""
XGBoost training script — offline training with walk-forward validation.

Trains one ForecasterRecursiveMultiSeries per commodity using district-pooled data.
Walk-forward validation RMSE/MAPE is logged to model_training_log BEFORE the
artifact file is written — if the log insert fails, no model is persisted.

Usage:
    cd backend
    python -m scripts.train_xgboost
"""
import sys
import json

# Windows console encoding fix
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
try:
    from skforecast.exceptions import MissingValuesWarning, InputTypeWarning
    warnings.filterwarnings("ignore", category=MissingValuesWarning)
    warnings.filterwarnings("ignore", category=InputTypeWarning)
except ImportError:
    pass

import gc
import numpy as np
import pandas as pd
from pathlib import Path
from decimal import Decimal
from typing import Optional

# Resolve repo root — this script lives at backend/scripts/train_xgboost.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MIN_DAYS_TRAIN = 730   # minimum days for XGBoost training (covers 365-day lag + buffer)
MIN_DAYS_SERVE = 365   # minimum days for serving (below → seasonal fallback)


def mape_to_confidence_colour(mape: Optional[float]) -> str:
    """Map MAPE value to a confidence colour for the UI.

    Green: MAPE < 10% (high confidence)
    Yellow: 10% <= MAPE < 25% (moderate confidence)
    Red: MAPE >= 25% or None (low confidence / missing data)
    """
    if mape is None:
        return "Red"
    if mape < 0.10:
        return "Green"
    if mape < 0.25:
        return "Yellow"
    return "Red"


def build_series_df(
    raw_df: pd.DataFrame,
    min_days: int = MIN_DAYS_TRAIN,
) -> tuple[pd.DataFrame, list[dict]]:
    """Build wide-format series DataFrame from raw price data.

    Args:
        raw_df: DataFrame with columns [price_date, district, modal_price]
        min_days: minimum date-span (max_date - min_date) in days to qualify

    Returns:
        series_df: Wide DataFrame with DatetimeIndex, columns = district names,
                   values = modal_price. Only districts with >= min_days span.
        excluded: List of dicts {"district": str, "reason": str} for filtered-out districts.
    """
    df = raw_df.copy()
    df["price_date"] = pd.to_datetime(df["price_date"])
    df["modal_price"] = df["modal_price"].astype("float32")

    # Cap to top MAX_DISTRICTS by observation count to limit pivot size
    MAX_DISTRICTS = 30
    district_counts = df.groupby("district").size().sort_values(ascending=False)
    top_districts = district_counts.head(MAX_DISTRICTS).index
    df = df[df["district"].isin(top_districts)]

    # Pivot to wide format: index=price_date, columns=district, values=modal_price
    wide = df.pivot_table(
        index="price_date",
        columns="district",
        values="modal_price",
        aggfunc="mean",
    )
    wide.index = pd.DatetimeIndex(wide.index)
    wide = wide.sort_index()

    # Create complete date range and reindex
    full_range = pd.date_range(start=wide.index.min(), end=wide.index.max(), freq="D")
    wide = wide.reindex(full_range)
    wide.index.name = "price_date"
    wide.index.freq = "D"

    # Forward-fill market closure gaps (limit=7 days to avoid filling long gaps)
    wide = wide.ffill(limit=7)

    # Linear interpolation for remaining interior gaps (limit=14 days)
    interp_limit = max(1, min(14, len(wide) - 1))
    wide = wide.interpolate(method="linear", limit=interp_limit, limit_direction="forward")

    # Trim trailing NaNs per column: find the last non-NaN index for each column
    # and crop to the earliest "last valid" across all kept columns after filtering.
    # This ensures the last_window is clean for skforecast.

    # Filter: only columns where date span >= min_days AND last 30 days are >=80% filled
    MAX_LAG = 30  # must match the largest lag used in the forecaster
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
        # Check that the tail (last_window region) is mostly filled
        tail = wide[col].iloc[-MAX_LAG:]
        fill_ratio = tail.notna().sum() / len(tail)
        if fill_ratio < 0.8:
            excluded.append({"district": col, "reason": "sparse_recent_data"})
            continue
        keep_cols.append(col)

    series_df = wide[keep_cols]

    # Final safety: fill any remaining NaNs with column median so the
    # forecaster never sees a NaN in X_train or last_window.
    for col in series_df.columns:
        if series_df[col].isna().any():
            series_df[col] = series_df[col].fillna(series_df[col].median())

    return series_df, excluded


def log_training(
    db,
    commodity: str,
    n_series: int,
    n_folds: int,
    rmse_arr: np.ndarray,
    mape_arr: np.ndarray,
    artifact_path: str,
    excluded: list[dict],
):
    """Insert ModelTrainingLog row. RAISES on DB error.

    The caller must NOT write the artifact file if this function raises.
    This enforces the no-model-without-validation invariant (FORE-02).
    """
    from app.models.model_training_log import ModelTrainingLog

    log_entry = ModelTrainingLog(
        commodity=commodity,
        n_series=n_series,
        n_folds=n_folds,
        rmse_fold_1=Decimal(str(round(float(rmse_arr[0]), 4))) if len(rmse_arr) > 0 else None,
        rmse_fold_2=Decimal(str(round(float(rmse_arr[1]), 4))) if len(rmse_arr) > 1 else None,
        rmse_fold_3=Decimal(str(round(float(rmse_arr[2]), 4))) if len(rmse_arr) > 2 else None,
        rmse_fold_4=Decimal(str(round(float(rmse_arr[3]), 4))) if len(rmse_arr) > 3 else None,
        rmse_mean=Decimal(str(round(float(rmse_arr.mean()), 4))),
        mape_mean=Decimal(str(round(float(mape_arr.mean()), 4))),
        artifact_path=artifact_path,
        skforecast_version=_get_skforecast_version(),
        xgboost_version=_get_xgboost_version(),
        excluded_districts=json.dumps(excluded) if excluded else None,
    )
    db.add(log_entry)
    db.commit()
    return log_entry


def _get_skforecast_version() -> str:
    """Get installed skforecast version."""
    try:
        import skforecast
        return skforecast.__version__
    except (ImportError, AttributeError):
        return "unknown"


def _get_xgboost_version() -> str:
    """Get installed xgboost version."""
    try:
        import xgboost as xgb_lib
        return xgb_lib.__version__
    except (ImportError, AttributeError):
        return "unknown"


def train_commodity(commodity: str, series_df: pd.DataFrame, excluded: list[dict], db) -> None:
    """Full train + validate + log + save cycle for one commodity.

    Steps:
    1. Create ForecasterRecursiveMultiSeries with XGBoost regressor
    2. Run walk-forward validation (4 folds)
    3. Log validation results to model_training_log (MUST succeed before writing artifact)
    4. Fit forecaster on all data
    5. Write .joblib artifact
    """
    import joblib
    from skforecast.recursive import ForecasterRecursiveMultiSeries
    from skforecast.model_selection import backtesting_forecaster_multiseries, TimeSeriesFold
    from xgboost import XGBRegressor

    # Lags: daily momentum + weekly + monthly + quarterly + semi-annual + annual
    # The 365-day lag preserves annual seasonality through recursive 365-step predictions
    forecaster = ForecasterRecursiveMultiSeries(
        regressor=XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            tree_method="hist",
            random_state=42,
        ),
        lags=[1, 7, 14, 30, 91, 182, 365],
        encoding="ordinal",
        transformer_series=None,
        dropna_from_series=True,
    )

    # Walk-forward validation: 4 folds, 30-day steps for stable R² measurement
    cv = TimeSeriesFold(
        steps=30,
        initial_train_size=int(len(series_df) * 0.7),
        refit=False,
        fixed_train_size=False,
    )

    from sklearn.metrics import r2_score as sklearn_r2

    metrics_df, predictions_df = backtesting_forecaster_multiseries(
        forecaster=forecaster,
        series=series_df,
        cv=cv,
        metric=["mean_squared_error", "mean_absolute_percentage_error"],
        n_jobs=1,
    )

    rmse_arr = np.sqrt(metrics_df["mean_squared_error"].values)
    mape_arr = metrics_df["mean_absolute_percentage_error"].values

    # Compute R² across all levels in the validation window
    try:
        actuals = series_df.loc[predictions_df.index]
        r2_scores = []
        for col in series_df.columns:
            pred_col = col if col in predictions_df.columns else None
            if pred_col and col in actuals.columns:
                y_true = actuals[col].dropna()
                y_pred = predictions_df[pred_col].loc[y_true.index].dropna()
                common = y_true.index.intersection(y_pred.index)
                if len(common) >= 10:
                    r2_scores.append(sklearn_r2(y_true[common], y_pred[common]))
        r2_mean = float(np.mean(r2_scores)) if r2_scores else float("nan")
    except Exception:
        r2_mean = float("nan")

    slug = commodity.lower().replace(" ", "_").replace("/", "_")
    artifact_path = str(ARTIFACTS_DIR / f"{slug}.joblib")

    # GATE: Log validation FIRST — artifact is only written if this succeeds
    log_training(
        db=db,
        commodity=commodity,
        n_series=len(series_df.columns),
        n_folds=4,
        rmse_arr=rmse_arr,
        mape_arr=mape_arr,
        artifact_path=artifact_path,
        excluded=excluded,
    )

    # Now fit on all data and save
    forecaster.fit(series=series_df)
    joblib.dump(forecaster, artifact_path)
    print(
        f"[OK] {commodity}: RMSE={rmse_arr.mean():.2f} "
        f"MAPE={mape_arr.mean():.4f} R²={r2_mean:.4f} -> {artifact_path}"
    )


def main():
    """Main entry point: iterate commodities, build series, train models."""
    from sqlalchemy.orm import Session
    from app.database.session import SessionLocal
    from app.models.price_history import PriceHistory
    from app.models.commodity import Commodity
    from app.models.mandi import Mandi
    from sqlalchemy import select, distinct
    from datetime import datetime, timedelta

    # Limit training data to last 5 years to reduce memory
    TRAIN_LOOKBACK_DAYS = 1825
    date_cutoff = (datetime.now() - timedelta(days=TRAIN_LOOKBACK_DAYS)).date()

    db = SessionLocal()
    try:
        # Get distinct commodity names by joining PriceHistory → Commodity
        commodities = db.execute(
            select(Commodity.id, Commodity.name)
            .join(PriceHistory, PriceHistory.commodity_id == Commodity.id)
            .distinct()
            .order_by(Commodity.name)
        ).all()

        print(f"Found {len(commodities)} commodities to process")

        for commodity_id, commodity_name in commodities:
            # Skip if model already trained
            slug = commodity_name.lower().replace(" ", "_").replace("/", "_")
            artifact_file = ARTIFACTS_DIR / f"{slug}.joblib"
            if artifact_file.exists():
                print(f"\n--- Skipping: {commodity_name} (already trained) ---")
                continue

            print(f"\n--- Processing: {commodity_name} ---")

            # Query price data joined with Mandi to get district (last 5 years only)
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
                print(
                    f"  [SKIP] Only {len(series_df.columns)} qualifying district(s) "
                    f"(need >= 2 for ForecasterRecursiveMultiSeries)"
                )
                continue

            print(
                f"  {len(series_df.columns)} qualifying districts, "
                f"{len(excluded)} excluded"
            )

            try:
                train_commodity(commodity_name, series_df, excluded, db)
            except Exception as e:
                print(f"  [ERROR] {commodity_name}: {e}")
            finally:
                # Free memory between commodities to prevent OOM
                raw_df = series_df = excluded = result = None
                gc.collect()

    finally:
        db.close()


if __name__ == "__main__":
    main()
