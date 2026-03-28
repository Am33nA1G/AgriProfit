"""train_forecast_v3.py — XGBoost + Prophet ensemble price forecaster.

Trains one Prophet model (national daily average) and one
ForecasterRecursiveMultiSeries (per-district XGBoost) per commodity.

Usage (from backend/ dir):
    ../.venv/Scripts/python.exe -m scripts.train_forecast_v3
Or directly:
    backend/.venv/Scripts/python.exe backend/scripts/train_forecast_v3.py
"""
import sys
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

from prophet import Prophet  # noqa: E402
from sklearn.metrics import r2_score as sklearn_r2  # noqa: E402
from xgboost import XGBRegressor  # noqa: E402
from skforecast.recursive import ForecasterRecursiveMultiSeries  # noqa: E402
import joblib  # noqa: E402

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_PATH = REPO_ROOT / "agmarknet_daily_10yr.parquet"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Config ─────────────────────────────────────────────────────────────────────
MIN_DAYS = 730          # min days of price data required to train
LAGS = [7, 14, 30, 91, 182, 365]
TEST_HORIZON = 365      # last 12 months held out for evaluation


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def build_fourier_exog(date_index: pd.DatetimeIndex) -> pd.DataFrame:
    """8 deterministic Fourier features from a DatetimeIndex."""
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


def build_national_series(df: pd.DataFrame) -> pd.DataFrame:
    """National daily mean price → {ds, y} DataFrame (Prophet format)."""
    national = (
        df.groupby("date")["price_modal"]
        .mean()
        .reset_index()
        .rename(columns={"date": "ds", "price_modal": "y"})
        .sort_values("ds")
    )
    idx = pd.date_range(national["ds"].min(), national["ds"].max(), freq="D")
    national = national.set_index("ds").reindex(idx).ffill().bfill()
    national.index.name = "ds"
    return national.reset_index()


def build_wide_series(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot date×district, ffill gaps ≤7 days, keep districts ≥ MIN_DAYS."""
    pivot = df.groupby(["date", "district"])["price_modal"].mean().unstack("district")
    coverage = pivot.notna().sum()
    pivot = pivot.loc[:, coverage >= MIN_DAYS]
    if pivot.empty:
        return pivot
    idx = pd.date_range(pivot.index.min(), pivot.index.max(), freq="D")
    pivot = pivot.reindex(idx).ffill(limit=7).bfill(limit=7)
    return pivot


def train_prophet(national_train: pd.DataFrame):
    """Fit Prophet on national train set. Returns (model, train_mape)."""
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10,
        n_changepoints=25,
    )
    exog = build_fourier_exog(pd.DatetimeIndex(national_train["ds"]))
    df = national_train.copy()
    for col in exog.columns:
        df[col] = exog[col].values
        m.add_regressor(col)
    m.fit(df)

    pred = m.predict(df)["yhat"].values
    y = national_train["y"].values
    mask = y > 0
    mape = float(np.mean(np.abs((y[mask] - pred[mask]) / y[mask]))) if mask.any() else 0.5
    return m, mape


def train_xgboost(wide_train: pd.DataFrame, exog_train: pd.DataFrame):
    """Fit ForecasterRecursiveMultiSeries with XGBoost."""
    xgb = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        tree_method="hist",
        random_state=42,
        verbosity=0,
    )
    forecaster = ForecasterRecursiveMultiSeries(regressor=xgb, lags=LAGS)
    forecaster.fit(series=wide_train, exog=exog_train)
    return forecaster


def compute_xgb_mape(forecaster, wide_test: pd.DataFrame, exog_test: pd.DataFrame) -> float:
    """MAPE on test set. skforecast 0.20+ returns long-format ['level','pred']."""
    try:
        pred_df = forecaster.predict(steps=len(wide_test), exog=exog_test)
        # Long format: columns = ['level', 'pred'], index = date (repeated per district)
        errors = []
        for col in wide_test.columns:
            dist_pred = pred_df[pred_df["level"] == col]["pred"].values
            y_true = wide_test[col].dropna().values
            n = min(len(dist_pred), len(y_true))
            if n == 0:
                continue
            mask = y_true[:n] > 0
            if mask.sum() > 0:
                errors.append(
                    np.mean(np.abs((y_true[:n][mask] - dist_pred[:n][mask]) / y_true[:n][mask]))
                )
        return float(np.mean(errors)) if errors else 0.5
    except Exception:
        return 0.5


def compute_ensemble_r2(
    prophet_model,
    xgb_forecaster,
    national_test: pd.DataFrame,
    wide_test: pd.DataFrame,
    exog_test: pd.DataFrame,
    alpha: float,
) -> float:
    """R² on held-out test period. Falls back to Prophet-only if XGBoost fails."""
    try:
        future = national_test.copy()
        exog = build_fourier_exog(pd.DatetimeIndex(national_test["ds"]))
        for col in exog.columns:
            future[col] = exog[col].values
        prophet_pred = prophet_model.predict(future)["yhat"].values

        try:
            xgb_pred_df = xgb_forecaster.predict(steps=len(wide_test), exog=exog_test)
            # Long format → mean across districts per date
            xgb_national = xgb_pred_df.groupby(level=0)["pred"].mean().values
            n = min(len(prophet_pred), len(xgb_national), len(national_test))
            ensemble = alpha * prophet_pred[:n] + (1 - alpha) * xgb_national[:n]
        except Exception:
            # XGBoost unavailable — evaluate Prophet alone
            n = min(len(prophet_pred), len(national_test))
            ensemble = prophet_pred[:n]

        y_true = national_test["y"].values[:n]
        return float(sklearn_r2(y_true, ensemble))
    except Exception:
        return 0.0


def process_commodity(parquet: pd.DataFrame, commodity: str) -> bool:
    """Train + save models for one commodity. Returns True on success/skip."""
    slug = slugify(commodity)
    meta_path = ARTIFACTS_DIR / f"{slug}_meta.json"

    if meta_path.exists():
        print("  [SKIP] already trained")
        return True

    df = parquet[parquet["commodity"].str.lower() == commodity.lower()].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["price_modal"])
    df = df[df["price_modal"] > 0]

    if df.empty:
        print("  [SKIP] no data")
        return False

    national = build_national_series(df)
    if len(national) < MIN_DAYS:
        print(f"  [SKIP] only {len(national)} days")
        return False

    last_data_date = str(national["ds"].max().date())
    split = max(0, len(national) - TEST_HORIZON)
    national_train = national.iloc[:split].copy()
    national_test = national.iloc[split:].copy()

    wide = build_wide_series(df)
    if wide.empty:
        print("  [SKIP] no districts with enough data")
        return False

    districts_list = wide.columns.tolist()
    exog_all = build_fourier_exog(wide.index)
    exog_train = exog_all.iloc[:split] if split < len(exog_all) else exog_all
    exog_test_df = (
        exog_all.iloc[split:] if split < len(exog_all) else exog_all.iloc[-TEST_HORIZON:]
    )
    wide_train = wide.iloc[:split] if split < len(wide) else wide
    wide_test = wide.iloc[split:] if split < len(wide) else wide.iloc[-TEST_HORIZON:]

    if len(national_train) < max(LAGS) + 10:
        print("  [SKIP] train window too small for lags")
        return False

    # Train Prophet
    prophet_model, prophet_mape = train_prophet(national_train.copy())

    # Train XGBoost
    xgb_forecaster = None
    xgb_mape = 0.5
    if len(wide_train) > max(LAGS):
        xgb_forecaster = train_xgboost(wide_train, exog_train)
        xgb_mape = compute_xgb_mape(xgb_forecaster, wide_test, exog_test_df)

    # MAPE-based alpha weighting
    inv_p = 1.0 / (prophet_mape + 1e-6)
    inv_x = 1.0 / (xgb_mape + 1e-6) if xgb_forecaster else 0.0
    alpha = inv_p / (inv_p + inv_x) if (inv_p + inv_x) > 0 else 1.0

    # Ensemble R²
    r2 = 0.0
    if xgb_forecaster and not wide_test.empty:
        r2 = compute_ensemble_r2(
            prophet_model, xgb_forecaster, national_test, wide_test, exog_test_df, alpha
        )

    # Save artifacts
    joblib.dump(prophet_model, ARTIFACTS_DIR / f"{slug}_prophet.joblib")
    if xgb_forecaster:
        joblib.dump(xgb_forecaster, ARTIFACTS_DIR / f"{slug}_xgboost.joblib")

    meta = {
        "alpha": alpha,
        "r2_score": r2,
        "prophet_mape": prophet_mape,
        "xgb_mape": xgb_mape,
        "last_data_date": last_data_date,
        "districts_list": districts_list,
        "trained_at": datetime.utcnow().isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    print(
        f"  [OK] R²={r2:.4f} alpha={alpha:.2f} "
        f"districts={len(districts_list)} prophet_mape={prophet_mape:.3f}"
    )
    return True


def main():
    print(f"Loading parquet: {PARQUET_PATH}")
    parquet = pd.read_parquet(
        PARQUET_PATH, columns=["date", "commodity", "district", "price_modal"]
    )
    print(f"Loaded {len(parquet):,} rows")

    commodities = sorted(parquet["commodity"].dropna().unique().tolist())
    print(f"{len(commodities)} unique commodities\n")

    ok = skip = err = 0
    for i, commodity in enumerate(commodities, 1):
        print(f"[{i:03d}/{len(commodities)}] {commodity}")
        try:
            result = process_commodity(parquet, commodity)
            if result:
                ok += 1
            else:
                skip += 1
        except Exception as e:
            print(f"  [ERR] {e}")
            err += 1

    print(f"\nDone. OK={ok}  SKIP={skip}  ERR={err}")


if __name__ == "__main__":
    main()
