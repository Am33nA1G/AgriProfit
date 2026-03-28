"""train_forecast_v4.py — Improved XGBoost + Prophet ensemble price forecaster.

Fixes over v3:
  - compute_xgb_mape(): proper skforecast 0.20+ long-format handling, verbose errors
  - Alpha clamped to [0.1, 0.9] — never fully single-model
  - R² computed per-district then weighted-median (no more cross-district compounding)
  - Weather + rainfall + price rolling features wired in (Phases 2/4)
  - Commodity tiering A/B/C/D: Prophet-only for sparse, seasonal fallback for minimal
  - Category-based XGBoost and Prophet configs (Phases 4/5)
  - Interval calibration stored in meta (Phase 6)
  - exog_columns stored in meta for serving-time alignment (Phase 4.7)
  - --force CLI flag for force-retrain
  - Artifacts written to ml/artifacts/v4/

Usage (from backend/ dir):
    ../.venv/Scripts/python.exe -m scripts.train_forecast_v4
    ../.venv/Scripts/python.exe -m scripts.train_forecast_v4 --force
    ../.venv/Scripts/python.exe -m scripts.train_forecast_v4 --commodity onion
    ../.venv/Scripts/python.exe -m scripts.train_forecast_v4 --workers 4
"""
import sys
import json
import logging
import warnings
import traceback
import argparse
from datetime import datetime
from pathlib import Path
from multiprocessing import Pool, cpu_count

import multiprocessing
import numpy as np
import pandas as pd

# Guard reconfigure — spawned workers on Windows may get a non-reconfigurable stdout
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
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
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts" / "v4"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("train_forecast_v4")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ── Config ─────────────────────────────────────────────────────────────────────
MIN_DAYS = 730          # min days of price data required to train
TEST_HORIZON = 365      # last 12 months held out for evaluation

# ── Tier definitions ───────────────────────────────────────────────────────────
COMMODITY_TIERS = {
    "A": {
        "strategy": "full_ensemble",
        "target_r2": 0.80,
    },
    "B": {
        "strategy": "full_ensemble",
        "target_r2": 0.65,
    },
    "C": {
        "strategy": "prophet_only",
        "target_r2": 0.50,
    },
    "D": {
        "strategy": "seasonal_average",
        "target_r2": None,
    },
}

# ── Category-based XGBoost configs ────────────────────────────────────────────
CROP_CATEGORY_CONFIGS = {
    "vegetables": {
        "n_estimators": 600,
        "max_depth": 8,
        "learning_rate": 0.02,
        "subsample": 0.7,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [1, 3, 7, 14, 30, 91],
    },
    "food_grains": {
        "n_estimators": 300,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "pulses": {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "oilseeds": {
        "n_estimators": 500,
        "max_depth": 7,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "spices": {
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.7,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [7, 14, 30, 91],
    },
    "fruits": {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "default": {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "lags": [7, 14, 30, 91, 182, 365],
    },
}

# ── Category-based Prophet configs ────────────────────────────────────────────
PROPHET_CONFIGS = {
    "vegetables": {
        "changepoint_prior_scale": 0.15,
        "seasonality_prior_scale": 5,
        "n_changepoints": 40,
        "seasonality_mode": "multiplicative",
    },
    "food_grains": {
        "changepoint_prior_scale": 0.03,
        "seasonality_prior_scale": 15,
        "n_changepoints": 20,
        "seasonality_mode": "additive",
    },
    "pulses": {
        "changepoint_prior_scale": 0.05,
        "seasonality_prior_scale": 10,
        "n_changepoints": 25,
        "seasonality_mode": "additive",
    },
    "oilseeds": {
        "changepoint_prior_scale": 0.07,
        "seasonality_prior_scale": 10,
        "n_changepoints": 30,
        "seasonality_mode": "additive",
    },
    "spices": {
        "changepoint_prior_scale": 0.20,
        "seasonality_prior_scale": 3,
        "n_changepoints": 50,
        "seasonality_mode": "multiplicative",
    },
    "fruits": {
        "changepoint_prior_scale": 0.10,
        "seasonality_prior_scale": 8,
        "n_changepoints": 30,
        "seasonality_mode": "multiplicative",
    },
    "default": {
        "changepoint_prior_scale": 0.05,
        "seasonality_prior_scale": 10,
        "n_changepoints": 25,
        "seasonality_mode": "additive",
    },
}

# ── Commodity → crop category maps ────────────────────────────────────────────
COMMODITY_CATEGORY_MAP = {
    # Vegetables
    "onion": "vegetables", "tomato": "vegetables", "potato": "vegetables",
    "brinjal": "vegetables", "cauliflower": "vegetables", "cabbage": "vegetables",
    "carrot": "vegetables", "green chilli": "vegetables", "lady finger": "vegetables",
    "bitter gourd": "vegetables", "ridge gourd": "vegetables", "bottle gourd": "vegetables",
    "pumpkin": "vegetables", "drumstick": "vegetables", "cluster beans": "vegetables",
    "french beans": "vegetables", "capsicum": "vegetables", "radish": "vegetables",
    "turnip": "vegetables", "spinach": "vegetables", "methi": "vegetables",
    # Food grains
    "rice": "food_grains", "wheat": "food_grains", "maize": "food_grains",
    "bajra": "food_grains", "jowar": "food_grains", "barley": "food_grains",
    "ragi": "food_grains", "corn": "food_grains",
    # Pulses
    "arhar (tur/red gram)": "pulses", "moong": "pulses", "urad": "pulses",
    "gram (chana)": "pulses", "lentil (masur)": "pulses", "peas": "pulses",
    "rajma": "pulses", "kulthi": "pulses", "moth beans": "pulses",
    # Oilseeds
    "groundnut": "oilseeds", "mustard": "oilseeds", "soybean": "oilseeds",
    "sunflower": "oilseeds", "sesame": "oilseeds", "linseed": "oilseeds",
    # Spices
    "turmeric": "spices", "chilli red": "spices", "coriander": "spices",
    "cumin": "spices", "ginger": "spices", "garlic": "spices", "pepper": "spices",
    "cardamom": "spices", "black pepper": "spices", "clove": "spices",
    # Fruits
    "mango": "fruits", "banana": "fruits", "apple": "fruits",
    "grapes": "fruits", "orange": "fruits", "papaya": "fruits",
    "pomegranate": "fruits", "guava": "fruits", "watermelon": "fruits",
    "lemon": "fruits", "pineapple": "fruits",
}

# Agmarknet category_id → crop type
CATEGORY_ID_TO_CROP_TYPE = {
    1: "vegetables",
    2: "fruits",
    3: "food_grains",
    4: "pulses",
    5: "oilseeds",
    6: "spices",
    7: "flowers",
    8: "miscellaneous",
}


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def get_xgb_config(commodity: str, category_id: int = None) -> dict:
    """Resolve XGBoost config by name then category_id fallback."""
    normalized = commodity.lower().strip()
    category = COMMODITY_CATEGORY_MAP.get(normalized)

    if not category and category_id is not None:
        category = CATEGORY_ID_TO_CROP_TYPE.get(int(category_id))
        if category:
            logger.debug("  [AUTO-CLASSIFY] '%s' → '%s' via category_id=%s", commodity, category, category_id)

    if not category:
        logger.debug("  [UNCATEGORIZED] '%s' — using default config", commodity)
        category = "default"

    return CROP_CATEGORY_CONFIGS.get(category, CROP_CATEGORY_CONFIGS["default"]), category


def get_prophet_config(category: str) -> dict:
    return PROPHET_CONFIGS.get(category, PROPHET_CONFIGS["default"])


# ── Data helpers ───────────────────────────────────────────────────────────────

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


def classify_commodity(df: pd.DataFrame, national: pd.DataFrame) -> str:
    """Assign commodity to tier A/B/C/D based on data quality."""
    n_districts = df["district"].nunique()
    n_days = len(national)

    if n_days < MIN_DAYS:
        return "D"
    if n_districts < 10:
        return "C"
    if n_districts >= 50:
        return "A"
    return "B"


# ── Feature builders ───────────────────────────────────────────────────────────

def build_national_price_exog(national_df: pd.DataFrame, wide_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    National-level rolling price features as shared exogenous.
    Uses shift(1) before rolling to prevent lookahead leakage.
    """
    series = national_df.set_index("ds")["y"]
    series = series.reindex(wide_index).ffill()

    lags = [7, 14, 30, 90]
    roll_windows = [7, 30]

    features = {}
    for lag in lags:
        features[f"price_lag_{lag}d"] = series.shift(lag)
    for window in roll_windows:
        shifted = series.shift(1)  # No lookahead
        features[f"price_roll_mean_{window}d"] = shifted.rolling(window).mean()
        features[f"price_roll_std_{window}d"] = shifted.rolling(window).std()

    price_feats = pd.DataFrame(features, index=wide_index)
    price_feats = price_feats.ffill().fillna(0)
    return price_feats


def build_weather_exog(wide_df: pd.DataFrame) -> pd.DataFrame | None:
    """Load monthly weather features, expand to daily, align to wide index."""
    weather_path = REPO_ROOT / "data" / "features" / "weather_monthly_features.parquet"
    if not weather_path.exists():
        return None

    try:
        wdf = pd.read_parquet(weather_path, engine="pyarrow")

        monthly = wdf.groupby(["year", "month"]).agg({
            col: "mean"
            for col in ["avg_temp_c", "avg_humidity", "rainfall_mm"]
            if col in wdf.columns
        }).reset_index()

        if monthly.empty:
            return None

        daily_records = []
        for _, row in monthly.iterrows():
            start = pd.Timestamp(year=int(row["year"]), month=int(row["month"]), day=1)
            end = start + pd.offsets.MonthEnd(0)
            days = pd.date_range(start, end, freq="D")
            for day in days:
                record = {"date": day}
                if "avg_temp_c" in monthly.columns:
                    record["weather_temp"] = row.get("avg_temp_c", np.nan)
                if "avg_humidity" in monthly.columns:
                    record["weather_humidity"] = row.get("avg_humidity", np.nan)
                if "rainfall_mm" in monthly.columns:
                    record["weather_rainfall"] = row.get("rainfall_mm", np.nan)
                if len(record) > 1:
                    daily_records.append(record)

        if not daily_records:
            return None

        weather_daily = pd.DataFrame(daily_records).set_index("date")
        weather_daily = weather_daily.reindex(wide_df.index).ffill().fillna(0)
        return weather_daily if not weather_daily.empty else None
    except Exception as e:
        logger.warning("  [WARN] Could not build weather exog: %s", e)
        return None


def build_rainfall_exog(wide_df: pd.DataFrame) -> pd.DataFrame | None:
    """Load rainfall data, align to wide index."""
    # Try multiple possible paths
    candidates = [
        REPO_ROOT / "data" / "ranifall_data" / "combined" / "rainfall_district_monthly.parquet",
        REPO_ROOT / "data" / "rainfall_data" / "combined" / "rainfall_district_monthly.parquet",
        REPO_ROOT / "data" / "features" / "rainfall_monthly_features.parquet",
    ]
    rainfall_path = next((p for p in candidates if p.exists()), None)
    if rainfall_path is None:
        return None

    try:
        rdf = pd.read_parquet(rainfall_path, engine="pyarrow")
        if "rainfall_mm" not in rdf.columns:
            return None

        group_cols = [c for c in ["year", "month"] if c in rdf.columns]
        if len(group_cols) < 2:
            return None

        monthly = rdf.groupby(group_cols).agg({"rainfall_mm": "mean"}).reset_index()

        daily_records = []
        for _, row in monthly.iterrows():
            start = pd.Timestamp(year=int(row["year"]), month=int(row["month"]), day=1)
            end = start + pd.offsets.MonthEnd(0)
            days = pd.date_range(start, end, freq="D")
            for day in days:
                daily_records.append({"date": day, "rainfall_mm": row["rainfall_mm"]})

        if not daily_records:
            return None

        rain_daily = pd.DataFrame(daily_records).set_index("date")
        rain_daily = rain_daily.reindex(wide_df.index).ffill().fillna(0)
        return rain_daily if not rain_daily.empty else None
    except Exception as e:
        logger.warning("  [WARN] Could not build rainfall exog: %s", e)
        return None


def build_all_exog(
    wide_df: pd.DataFrame,
    national_df: pd.DataFrame,
) -> pd.DataFrame:
    """Unified exogenous builder: Fourier + price rolling + weather + rainfall."""
    parts = [build_fourier_exog(wide_df.index)]

    price_exog = build_national_price_exog(national_df, wide_df.index)
    if price_exog is not None and not price_exog.empty:
        parts.append(price_exog)

    weather_exog = build_weather_exog(wide_df)
    if weather_exog is not None and not weather_exog.empty:
        parts.append(weather_exog)

    rainfall_exog = build_rainfall_exog(wide_df)
    if rainfall_exog is not None and not rainfall_exog.empty:
        parts.append(rainfall_exog)

    combined = pd.concat(parts, axis=1)
    combined = combined.ffill().fillna(0)

    # Drop constant columns — no predictive value
    nunique = combined.nunique()
    combined = combined.loc[:, nunique > 1]

    return combined


# ── Model trainers ─────────────────────────────────────────────────────────────

def train_prophet(
    national_train: pd.DataFrame,
    prophet_config: dict,
    weather_exog: pd.DataFrame | None = None,
) -> tuple:
    """Fit Prophet on national train set. Returns (model, train_mape)."""
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=prophet_config["changepoint_prior_scale"],
        seasonality_prior_scale=prophet_config["seasonality_prior_scale"],
        n_changepoints=prophet_config["n_changepoints"],
        seasonality_mode=prophet_config.get("seasonality_mode", "additive"),
    )

    # Indian monsoon + crop cycle seasonalities
    m.add_seasonality(name="monsoon", period=365.25 / 3, fourier_order=3)
    m.add_seasonality(name="crop_cycle", period=365.25 / 2, fourier_order=5)

    exog = build_fourier_exog(pd.DatetimeIndex(national_train["ds"]))
    df = national_train.copy()
    for col in exog.columns:
        df[col] = exog[col].values
        m.add_regressor(col)

    # Add weather regressors if available
    if weather_exog is not None and not weather_exog.empty:
        aligned = weather_exog.reindex(pd.DatetimeIndex(national_train["ds"]))
        for col in aligned.columns:
            if aligned[col].nunique() > 1:
                df[col] = aligned[col].fillna(0).values
                m.add_regressor(col)

    m.fit(df)

    pred = m.predict(df)["yhat"].values
    y = national_train["y"].values
    mask = y > 0
    mape = float(np.mean(np.abs((y[mask] - pred[mask]) / y[mask]))) if mask.any() else 0.5
    return m, mape


def train_xgboost(
    wide_train: pd.DataFrame,
    exog_train: pd.DataFrame,
    config: dict,
) -> "ForecasterRecursiveMultiSeries":
    """Fit ForecasterRecursiveMultiSeries with category-specific XGBoost config."""
    xgb = XGBRegressor(
        n_estimators=config["n_estimators"],
        max_depth=config["max_depth"],
        learning_rate=config["learning_rate"],
        subsample=config.get("subsample", 0.8),
        colsample_bytree=config.get("colsample_bytree", 0.8),
        min_child_weight=config.get("min_child_weight", 3),
        tree_method="hist",
        random_state=42,
        verbosity=0,
    )
    lags = config.get("lags", [7, 14, 30, 91, 182, 365])
    forecaster = ForecasterRecursiveMultiSeries(regressor=xgb, lags=lags)
    forecaster.fit(series=wide_train, exog=exog_train)
    return forecaster


# ── Evaluation ─────────────────────────────────────────────────────────────────

def _xgb_predict_wide(xgb_forecaster, n_steps: int, exog_slice) -> pd.DataFrame | None:
    """
    Helper to call xgb_forecaster.predict() and normalise the result to wide format.
    skforecast 0.20+ returns long format with a 'level' column.
    Returns a wide DataFrame (columns = district names) or None on failure.
    """
    try:
        pred_df = xgb_forecaster.predict(steps=n_steps, exog=exog_slice)
    except Exception as e:
        logger.warning("  [WARN] xgb predict() failed: %s", e)
        return None

    if isinstance(pred_df.index, pd.MultiIndex):
        return pred_df["pred"].unstack(level="level")
    elif "level" in pred_df.columns:
        return pred_df.pivot_table(index=pred_df.index, columns="level", values="pred")
    else:
        # Already wide (older skforecast) or unknown — return as-is
        return pred_df if isinstance(pred_df, pd.DataFrame) else None


def compute_xgb_mape(
    forecaster,
    wide_test: pd.DataFrame,
    exog_test: pd.DataFrame,
) -> float:
    """
    MAPE on test set — handles skforecast 0.20+ long-format output.

    Key fixes over v3:
    - Handles both MultiIndex and flat long-format outputs
    - Uses median (outlier-resistant) instead of mean
    - Prints actual exception instead of silently swallowing it
    - Caps prediction steps to avoid memory issues
    """
    if wide_test.empty:
        return 0.5

    try:
        n_steps = min(len(wide_test), 365)
        exog_slice = exog_test.iloc[:n_steps] if exog_test is not None and not exog_test.empty else None

        pred_wide = _xgb_predict_wide(forecaster, n_steps, exog_slice)
        if pred_wide is None:
            return 0.5

        errors = []
        for col in wide_test.columns:
            if col not in pred_wide.columns:
                continue
            y_true = wide_test[col].dropna().values
            y_pred = pred_wide[col].dropna().values
            n = min(len(y_true), len(y_pred))
            if n == 0:
                continue
            mask = y_true[:n] > 0
            if mask.sum() > 0:
                district_mape = float(
                    np.mean(np.abs((y_true[:n][mask] - y_pred[:n][mask]) / y_true[:n][mask]))
                )
                errors.append(district_mape)

        if not errors:
            return 0.5

        return float(np.median(errors))
    except Exception as e:
        logger.warning("  [WARN] XGB MAPE computation failed: %s", e)
        traceback.print_exc()
        return 0.5


def compute_ensemble_r2_v2(
    prophet_model,
    xgb_forecaster,
    national_test: pd.DataFrame,
    wide_test: pd.DataFrame,
    exog_test: pd.DataFrame,
    alpha: float,
) -> tuple[float, dict]:
    """
    Per-district R² then weighted median.
    Fix over v3: no cross-district averaging → no compounded outlier errors.
    Returns (overall_r2, per_district_r2_dict).
    """
    # Prophet prediction (national line)
    future = national_test.copy()
    exog = build_fourier_exog(pd.DatetimeIndex(national_test["ds"]))
    for col in exog.columns:
        future[col] = exog[col].values
    # Fill any extra regressors the model was trained with (e.g. weather_temp) using 0
    for col in prophet_model.extra_regressors:
        if col not in future.columns:
            future[col] = 0.0
    prophet_pred = prophet_model.predict(future)["yhat"].values

    # XGBoost wide prediction
    xgb_wide = None
    if xgb_forecaster is not None:
        n_steps = min(len(wide_test), 365)
        exog_slice = exog_test.iloc[:n_steps] if exog_test is not None and not exog_test.empty else None
        xgb_wide = _xgb_predict_wide(xgb_forecaster, n_steps, exog_slice)

    if xgb_wide is None:
        # Evaluate Prophet alone
        n = min(len(prophet_pred), len(national_test))
        y_true = national_test["y"].values[:n]
        r2 = float(sklearn_r2(y_true, prophet_pred[:n]))
        return r2, {"national_prophet_only": r2}

    # Per-district ensemble R²
    district_r2s = {}
    district_weights = {}
    for col in wide_test.columns:
        y_true = wide_test[col].dropna().values
        if col not in xgb_wide.columns:
            continue
        y_xgb = xgb_wide[col].dropna().values
        n = min(len(y_true), len(y_xgb), len(prophet_pred))
        if n < 14:
            continue
        ensemble = alpha * prophet_pred[:n] + (1 - alpha) * y_xgb[:n]
        try:
            r2 = float(sklearn_r2(y_true[:n], ensemble))
            district_r2s[col] = r2
            district_weights[col] = n
        except Exception:
            continue

    if not district_r2s:
        return 0.0, {}

    # Weighted median R²
    items = sorted(district_r2s.items(), key=lambda x: x[1])
    weights = [district_weights[k] for k, _ in items]
    values = [v for _, v in items]
    cumw = np.cumsum(weights) / np.sum(weights)
    median_idx = int(np.searchsorted(cumw, 0.5))
    overall_r2 = values[min(median_idx, len(values) - 1)]

    return overall_r2, district_r2s


def calibrate_intervals(
    prophet_model,
    national_test: pd.DataFrame,
) -> float:
    """
    Returns empirical coverage of Prophet's 80% interval on held-out test data.
    Well-calibrated: ~0.80. Below 0.60 → widen intervals at serve time.
    """
    try:
        future = national_test.copy()
        exog = build_fourier_exog(pd.DatetimeIndex(national_test["ds"]))
        for col in exog.columns:
            future[col] = exog[col].values
        for col in prophet_model.extra_regressors:
            if col not in future.columns:
                future[col] = 0.0
        forecast = prophet_model.predict(future)

        actual = national_test["y"].values
        lower = forecast["yhat_lower"].values
        upper = forecast["yhat_upper"].values
        n = min(len(actual), len(lower))

        in_interval = np.mean((actual[:n] >= lower[:n]) & (actual[:n] <= upper[:n]))
        return float(in_interval)
    except Exception:
        return 0.80  # Default if calibration fails


def save_seasonal_fallback(slug: str, national: pd.DataFrame) -> None:
    """Save monthly price statistics as seasonal fallback for Tier D commodities."""
    df = national.copy()
    df["month"] = pd.to_datetime(df["ds"]).dt.month
    result = {}
    for month, grp in df.groupby("month"):
        prices = grp["y"].dropna()
        prices = prices[prices > 0]
        if len(prices) < 5:
            continue
        result[str(int(month))] = {
            "mean":   round(float(prices.mean()), 2),
            "median": round(float(prices.median()), 2),
            "p10":    round(float(prices.quantile(0.10)), 2),
            "p25":    round(float(prices.quantile(0.25)), 2),
            "p75":    round(float(prices.quantile(0.75)), 2),
            "p90":    round(float(prices.quantile(0.90)), 2),
        }
    out = ARTIFACTS_DIR / f"{slug}_seasonal.json"
    out.write_text(json.dumps(result, indent=2))


# ── Main commodity processor ───────────────────────────────────────────────────

def process_commodity(args: tuple) -> bool:
    """Train + save models for one commodity. Returns True on success/skip."""
    commodity, force = args
    try:
        return _process_commodity_inner(commodity, force)
    except Exception as e:
        logger.error("  [ERR] %s: unhandled exception: %s", commodity, e)
        traceback.print_exc()
        return False


def _process_commodity_inner(commodity: str, force: bool) -> bool:
    """Inner implementation — wrapped by process_commodity for worker safety."""
    slug = slugify(commodity)
    meta_path = ARTIFACTS_DIR / f"{slug}_meta.json"

    if meta_path.exists() and not force:
        logger.info("  [SKIP] %s already trained (use --force to retrain)", commodity)
        return True

    # Load parquet here to avoid passing large DataFrame through multiprocessing
    try:
        parquet = pd.read_parquet(
            PARQUET_PATH,
            engine="pyarrow",
            filters=[("commodity", "==", commodity)],
            columns=["date", "commodity", "district", "price_modal", "category_id"]
            if True else ["date", "commodity", "district", "price_modal"],
        )
    except Exception:
        # category_id may not be in parquet — fall back
        try:
            parquet = pd.read_parquet(
                PARQUET_PATH,
                engine="pyarrow",
                filters=[("commodity", "==", commodity)],
                columns=["date", "commodity", "district", "price_modal"],
            )
        except Exception as e:
            logger.error("  [ERR] Could not load parquet for %s: %s", commodity, e)
            return False

    df = parquet[parquet["commodity"].str.lower() == commodity.lower()].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["price_modal"])
    df = df[df["price_modal"] > 0]

    if df.empty:
        logger.info("  [SKIP] %s: no data", commodity)
        return False

    # Resolve commodity category
    category_id = int(df["category_id"].iloc[0]) if "category_id" in df.columns and not df["category_id"].isna().all() else None
    xgb_config, category = get_xgb_config(commodity, category_id)
    prophet_config = get_prophet_config(category)

    national = build_national_series(df)
    if len(national) < MIN_DAYS:
        logger.info("  [SKIP] %s: only %d days", commodity, len(national))
        return False

    # Classify tier
    tier = classify_commodity(df, national)
    tier_strategy = COMMODITY_TIERS[tier]["strategy"]

    last_data_date = str(national["ds"].max().date())

    # Tier D → seasonal fallback only
    if tier_strategy == "seasonal_average":
        save_seasonal_fallback(slug, national)
        meta = {
            "tier": tier,
            "commodity_category": category,
            "strategy": "seasonal_average",
            "last_data_date": last_data_date,
            "trained_at": datetime.utcnow().isoformat(),
        }
        meta_path.write_text(json.dumps(meta, indent=2))
        logger.info("  [TIER-D] %s — seasonal fallback saved", commodity)
        return True

    split = max(0, len(national) - TEST_HORIZON)
    national_train = national.iloc[:split].copy()
    national_test = national.iloc[split:].copy()

    wide = build_wide_series(df)
    if wide.empty:
        logger.info("  [SKIP] %s: no districts with enough data", commodity)
        return False

    districts_list = wide.columns.tolist()
    n_districts = len(districts_list)

    # Build exog only for full_ensemble; for prophet_only use Fourier-only
    if tier_strategy == "full_ensemble":
        exog_all = build_all_exog(wide, national)
    else:
        exog_all = build_fourier_exog(wide.index)

    exog_train = exog_all.iloc[:split] if split < len(exog_all) else exog_all
    exog_test_df = (
        exog_all.iloc[split:] if split < len(exog_all) else exog_all.iloc[-TEST_HORIZON:]
    )
    wide_train = wide.iloc[:split] if split < len(wide) else wide
    wide_test = wide.iloc[split:] if split < len(wide) else wide.iloc[-TEST_HORIZON:]

    min_lag = min(xgb_config.get("lags", [365]))
    if len(national_train) < min_lag + 10:
        logger.info("  [SKIP] %s: train window too small for lags", commodity)
        return False

    # Extract weather exog for prophet regressors
    weather_exog_for_prophet = build_weather_exog(wide_train) if tier_strategy == "full_ensemble" else None

    # Train Prophet
    prophet_model, prophet_mape = train_prophet(national_train.copy(), prophet_config, weather_exog_for_prophet)

    # Train XGBoost (only for Tier A/B)
    xgb_forecaster = None
    xgb_mape = None
    alpha = 1.0  # Prophet-only default

    if tier_strategy == "full_ensemble" and len(wide_train) > max(xgb_config.get("lags", [365])):
        xgb_forecaster = train_xgboost(wide_train, exog_train, xgb_config)
        xgb_mape = compute_xgb_mape(xgb_forecaster, wide_test, exog_test_df)

        # Alpha: inverse-MAPE weighted, clamped to [0.1, 0.9]
        inv_p = 1.0 / (prophet_mape + 1e-6)
        inv_x = 1.0 / (xgb_mape + 1e-6)
        raw_alpha = inv_p / (inv_p + inv_x)
        alpha = max(0.1, min(0.9, raw_alpha))

    # Ensemble R²
    r2 = 0.0
    per_district_r2 = {}
    if not wide_test.empty:
        r2, per_district_r2 = compute_ensemble_r2_v2(
            prophet_model, xgb_forecaster, national_test, wide_test, exog_test_df, alpha
        )

    # Interval calibration
    interval_coverage = calibrate_intervals(prophet_model, national_test)

    # Save artifacts
    prophet_path = ARTIFACTS_DIR / f"{slug}_prophet.joblib"
    joblib.dump(prophet_model, prophet_path)
    if xgb_forecaster is not None:
        joblib.dump(xgb_forecaster, ARTIFACTS_DIR / f"{slug}_xgboost.joblib")

    meta = {
        "alpha": round(alpha, 4),
        "r2_score": round(r2, 4),
        "r2_per_district": {k: round(v, 4) for k, v in per_district_r2.items()},
        "prophet_mape": round(prophet_mape, 4),
        "xgb_mape": round(xgb_mape, 4) if xgb_mape is not None else None,
        "tier": tier,
        "commodity_category": category,
        "strategy": tier_strategy,
        "n_districts": n_districts,
        "last_data_date": last_data_date,
        "districts_list": districts_list,
        "exog_columns": list(exog_all.columns),
        "interval_coverage_80pct": round(interval_coverage, 4),
        "trained_at": datetime.utcnow().isoformat(),
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    logger.info(
        "  [OK] %s  tier=%s  R²=%.4f  alpha=%.2f  n_dist=%d  prophet_mape=%.3f  xgb_mape=%s",
        commodity, tier, r2, alpha, n_districts, prophet_mape,
        f"{xgb_mape:.3f}" if xgb_mape is not None else "N/A",
    )
    return True


# ── Entry point ────────────────────────────────────────────────────────────────

def get_all_commodities() -> list[str]:
    """Load all commodity names from parquet."""
    parquet = pd.read_parquet(PARQUET_PATH, engine="pyarrow", columns=["commodity"])
    return sorted(parquet["commodity"].dropna().unique().tolist())


def main(force: bool = False, commodity: str | None = None, workers: int = 1):
    logger.info("Loading commodity list from: %s", PARQUET_PATH)

    commodities = get_all_commodities()
    if commodity:
        commodities = [c for c in commodities if c.lower() == commodity.lower()]
        if not commodities:
            logger.error("Commodity '%s' not found in parquet", commodity)
            return 0, 1

    logger.info("%d commodities to train (force=%s, workers=%d)", len(commodities), force, workers)

    args = [(c, force) for c in commodities]

    if workers > 1:
        n_workers = min(workers, cpu_count(), len(commodities))
        logger.info("Spawning %d parallel workers…", n_workers)
        with Pool(processes=n_workers) as pool:
            results = pool.map(process_commodity, args)
    else:
        results = [process_commodity(a) for a in args]

    successes = sum(1 for r in results if r)
    failures = len(results) - successes
    logger.info("Complete: %d/%d succeeded, %d failed", successes, len(commodities), failures)
    return successes, failures


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Required for Windows multiprocessing with PyInstaller / spawn
    parser = argparse.ArgumentParser(description="Train v4 price forecast models")
    parser.add_argument("--force", action="store_true", help="Retrain all commodities even if already trained")
    parser.add_argument("--commodity", type=str, default=None, help="Train a single commodity only")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker count (default: 1)")
    cli_args = parser.parse_args()

    main(force=cli_args.force, commodity=cli_args.commodity, workers=cli_args.workers)
