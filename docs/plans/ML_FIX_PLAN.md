# ML Pipeline — Comprehensive Fix Plan

> **Goal**: Raise ensemble R² to 0.8–0.9 for high-data commodities and ≥ 0.6 for the rest.
> **Current state**: 248/256 commodities have R² < 0.6; median R² = −0.996.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Root Cause Inventory](#2-root-cause-inventory)
3. [Phase 1 — Critical Bug Fixes](#3-phase-1--critical-bug-fixes)
4. [Phase 2 — Feature Engineering Integration](#4-phase-2--feature-engineering-integration)
5. [Phase 3 — Commodity Tiering & Adaptive Training](#5-phase-3--commodity-tiering--adaptive-training)
6. [Phase 4 — Hyperparameter Tuning](#6-phase-4--hyperparameter-tuning)
7. [Phase 5 — Prophet Improvements](#7-phase-5--prophet-improvements)
8. [Phase 6 — Ensemble & Evaluation Fixes](#8-phase-6--ensemble--evaluation-fixes)
9. [Phase 7 — Confidence Gating in Serving Layer](#9-phase-7--confidence-gating-in-serving-layer)
10. [Phase 8 — Yield Model Fixes](#10-phase-8--yield-model-fixes)
11. [Phase 9 — Retraining Pipeline & CI](#11-phase-9--retraining-pipeline--ci)
12. [Phase 10 — Monitoring & Drift Detection](#12-phase-10--monitoring--drift-detection)
13. [Implementation Order & Timeline](#13-implementation-order--timeline)
14. [Success Metrics](#14-success-metrics)
15. [Risk Log](#15-risk-log)

---

## 1. Executive Summary

The ML pipeline has **5 category-level** and **7 code-level** problems producing near-useless predictions for ~97% of commodities:

| # | Problem | Impact | Effort |
|---|---------|--------|--------|
| 1 | `compute_xgb_mape()` always returns 0.5 | Alpha weighting broken → ensemble is ~50/50 blind mix | 1 hr |
| 2 | Ensemble R² computed nationally across all districts | Negative R² from extreme outlier districts | 2 hr |
| 3 | Feature modules exist but are NOT wired into training | XGBoost sees ONLY lags + Fourier — no weather, rainfall, soil, or price features | 8 hr |
| 4 | One-size-fits-all hyperparameters | Volatile vegetables, stable grains, sparse spices all get identical config | 4 hr |
| 5 | Prophet config not tuned per commodity type | changepoint_prior_scale=0.05 too conservative for volatile crops | 3 hr |
| 6 | No quality gate — broken models served as "full model" | Users get wildly wrong forecasts with Green confidence | 4 hr |
| 7 | 120+ commodities have <10 districts | Multi-series XGBoost can't learn cross-district patterns | 2 hr |

---

## 2. Root Cause Inventory

### 2.1 Bug: `compute_xgb_mape()` — Silent Exception → Hardcoded 0.5

**File**: `backend/scripts/train_forecast_v3.py`, lines ~145–165

```python
def compute_xgb_mape(forecaster, wide_test, exog_test) -> float:
    try:
        pred_df = forecaster.predict(steps=len(wide_test), exog=exog_test)
        # ... MAPE computation ...
    except Exception:      # ← catches EVERYTHING silently
        return 0.5         # ← ALL 256 commodities hit this path
```

**Evidence**: Every `_meta.json` has `"xgb_mape": 0.5` (verified across all 256 files).

**Root cause**: skforecast 0.20+ returns predictions in **long format** (`level`, `pred` columns) but the index alignment between `wide_test` and prediction dates is wrong — lengths don't match, causing an index error inside the try block.

### 2.2 Bug: Alpha Weighting Is Garbage

Because `xgb_mape` is always 0.5:
```
alpha = inv_prophet / (inv_prophet + inv_xgb)
      = (1/prophet_mape) / (1/prophet_mape + 1/0.5)
      = (1/prophet_mape) / (1/prophet_mape + 2)
```
For typical prophet_mape ≈ 0.15: `alpha ≈ 0.77` — always heavily Prophet-weighted regardless of actual XGB quality.

### 2.3 Structural: R² Computed Nationally

`compute_ensemble_r2()` computes mean XGBoost prediction across districts → compares to national mean price → single R². If any district has wildly wrong predictions, it drags the mean far from the national price, producing deeply negative R².

### 2.4 Structural: Feature Modules Not Used

Four well-implemented feature modules exist but **NONE** are imported or called by `train_forecast_v3.py`:

| Module | Features | Status |
|--------|----------|--------|
| `ml/price_features.py` | `price_lag_{n}d`, `price_roll_mean_{n}d`, `price_roll_std_{n}d` | **NOT WIRED** |
| `ml/rainfall_features.py` | `rainfall_deficit_pct`, `rainfall_mm` | **NOT WIRED** |
| `ml/weather_features.py` | `max_temp`, `min_temp`, `avg_temp`, `humidity`, `wind_speed` | **NOT WIRED** |
| `ml/soil_features.py` | 15 NPK/pH features | **NOT WIRED** |

Training currently uses ONLY:
- Prophet: Fourier harmonics (8 features)
- XGBoost: lagged price values only (lags=[7,14,30,91,182,365])

### 2.5 Structural: One Config For All

```python
# Same for ALL 256 commodities:
n_estimators=400, max_depth=6, learning_rate=0.03
changepoint_prior_scale=0.05, seasonality_prior_scale=10
```

Onion (volatile, 10-day swings) needs different config than Wheat (slow-moving, seasonal).

### 2.6 Structural: No Quality Gate

In `forecast/service.py`, ANY commodity model is served:
```python
meta = load_meta(slug)
# No R² check — broken models (R² = -50) served with "full model" tier
```

### 2.7 Data: Sparse Commodities

120+ commodities have <10 districts in the data. `ForecasterRecursiveMultiSeries` needs sufficient cross-series variation to learn meaningful patterns.

---

## 3. Phase 1 — Critical Bug Fixes

### 3.1 Fix `compute_xgb_mape()`

**File**: `backend/scripts/train_forecast_v3.py`

**Problem**: The prediction alignment is broken. `forecaster.predict()` returns dates starting from the end of the training data, but `wide_test` index may not align perfectly.

**Fix**:

```python
def compute_xgb_mape(
    forecaster,
    wide_test: pd.DataFrame,
    exog_test: pd.DataFrame,
) -> float:
    """MAPE on test set — handles skforecast 0.20+ long-format output."""
    if wide_test.empty:
        return 0.5

    try:
        n_steps = min(len(wide_test), 365)  # Cap prediction horizon
        exog_slice = exog_test.iloc[:n_steps] if exog_test is not None else None
        pred_df = forecaster.predict(steps=n_steps, exog=exog_slice)

        # skforecast 0.20+ long format: columns=['level', 'pred'] with date index
        # NOTE: column is 'level' (singular) — NOT 'levels'
        if isinstance(pred_df.index, pd.MultiIndex):
            pred_wide = pred_df["pred"].unstack(level="level")
        elif "level" in pred_df.columns:
            pred_wide = pred_df.pivot_table(
                index=pred_df.index, columns="level", values="pred",
            )
        else:
            pred_wide = pred_df  # Already wide format (older skforecast)

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
            return 0.5  # Genuine fallback: no overlap at all

        return float(np.median(errors))  # Median is more robust than mean
    except Exception as e:
        import traceback
        print(f"  [WARN] XGB MAPE computation failed: {e}")
        traceback.print_exc()
        return 0.5  # Still fallback, but now we'll see WHY
```

**Key changes**:
1. Handle both MultiIndex and flat long-format outputs
2. Use `median` instead of `mean` (outlier-resistant)
3. **Print the actual error** instead of silently swallowing it
4. Cap prediction steps to avoid memory issues
5. Use `"level"` (singular) — `"levels"` is incorrect and would silently fall to the `elif` branch

### 3.2 Fix Alpha Computation

Same file — currently correct formula but bad inputs. Once XGB MAPE is fixed, alpha will self-correct. However, add a guard:

```python
# After computing alpha:
alpha = max(0.1, min(0.9, alpha))  # Clamp: never go fully one-model
```

### 3.3 Remove Skip-If-Already-Trained Gate During Fix

**File**: `backend/scripts/train_forecast_v3.py`, inside `process_commodity()`

```python
# REMOVE THIS during the fix cycle:
if meta_path.exists():
    print("  [SKIP] already trained")
    return True
```

Replace with:
```python
# Allow retraining with --force flag
if meta_path.exists() and not FORCE_RETRAIN:
    print("  [SKIP] already trained (use --force to retrain)")
    return True
```

Add CLI argument:
```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--force", action="store_true", help="Retrain all commodities")
args = parser.parse_args()
FORCE_RETRAIN = args.force
```

### 3.4 Fix Deprecated pandas API (Global)

Every `fillna(method="ffill")` in the codebase raises `FutureWarning` in pandas 2.x and will break in pandas 3.x.

**Find and replace throughout all training scripts:**
```python
# WRONG (deprecated):
df.fillna(method="ffill")

# CORRECT:
df.ffill()
```

This applies to every occurrence in `train_forecast_v3.py`, `build_all_exog()`, and any feature-building helper.

---

## 4. Phase 2 — Feature Engineering Integration

### 4.1 Wire Price Features Into XGBoost Training — With Leakage Prevention

**File**: `backend/scripts/train_forecast_v3.py`

**Current state**: XGBoost only uses lags (via skforecast) + Fourier exogenous. No rolling stats.

> **Critical**: Rolling price features MUST use `shift(1)` before rolling to ensure the window ends *yesterday*, not today. Without this guard, training data leaks future prices into the feature, producing artificially high training R² and poor test performance.

```python
from app.ml.price_features import compute_price_features

def compute_price_features_safe(
    series: pd.Series,
    lags: list,
    roll_windows: list,
) -> pd.DataFrame:
    """
    Compute rolling price features with strict no-lookahead guarantee.
    shift(lag) ensures we only see price from `lag` days ago.
    shift(1) before rolling ensures the window ends YESTERDAY, not today.
    """
    features = {}
    for lag in lags:
        features[f"price_lag_{lag}d"] = series.shift(lag)
    for window in roll_windows:
        shifted = series.shift(1)  # No lookahead
        features[f"price_roll_mean_{window}d"] = shifted.rolling(window).mean()
        features[f"price_roll_std_{window}d"]  = shifted.rolling(window).std()
    return pd.DataFrame(features, index=series.index)

def build_national_price_exog(national_df: pd.DataFrame, wide_index) -> pd.DataFrame:
    """National-level rolling price features as shared exogenous."""
    series = national_df.set_index("ds")["y"]
    price_feats = compute_price_features_safe(
        series,
        lags=[7, 14, 30, 90],
        roll_windows=[7, 30],
    )
    # Align to wide DataFrame index
    price_feats = price_feats.reindex(wide_index).ffill().fillna(0)
    return price_feats
```

### 4.2 Wire Weather Features Into XGBoost Training

**File**: `backend/scripts/train_forecast_v3.py`

```python
from app.ml.weather_features import compute_weather_features

def build_weather_exog(wide_df: pd.DataFrame) -> pd.DataFrame | None:
    """Load monthly weather features, expand to daily, align to wide index."""
    weather_path = REPO_ROOT / "data" / "features" / "weather_monthly_features.parquet"
    if not weather_path.exists():
        return None

    wdf = pd.read_parquet(weather_path, engine="pyarrow")

    # Compute national average weather per month
    monthly = wdf.groupby(["year", "month"]).agg({
        "avg_temp_c": "mean",
        "avg_humidity": "mean",
        "rainfall_mm": "mean",
    }).reset_index()

    # Expand monthly → daily
    daily_records = []
    for _, row in monthly.iterrows():
        start = pd.Timestamp(year=int(row["year"]), month=int(row["month"]), day=1)
        end = start + pd.offsets.MonthEnd(0)
        days = pd.date_range(start, end, freq="D")
        for day in days:
            daily_records.append({
                "date": day,
                "weather_temp": row["avg_temp_c"],
                "weather_humidity": row["avg_humidity"],
                "weather_rainfall": row["rainfall_mm"],
            })

    weather_daily = pd.DataFrame(daily_records).set_index("date")
    weather_daily = weather_daily.reindex(wide_df.index).ffill().fillna(0)
    return weather_daily
```

### 4.3 Wire Rainfall Features

```python
from app.ml.rainfall_features import compute_rainfall_features

def build_rainfall_exog(wide_df: pd.DataFrame) -> pd.DataFrame | None:
    """Load rainfall data, compute deficit, align to wide index."""
    rainfall_path = REPO_ROOT / "data" / "rainfall_data" / "combined" / "rainfall_district_monthly.parquet"
    if not rainfall_path.exists():
        return None

    rdf = pd.read_parquet(rainfall_path, engine="pyarrow")
    monthly = rdf.groupby(["year", "month"]).agg({"rainfall_mm": "mean"}).reset_index()

    daily_records = []
    for _, row in monthly.iterrows():
        start = pd.Timestamp(year=int(row["year"]), month=int(row["month"]), day=1)
        end = start + pd.offsets.MonthEnd(0)
        days = pd.date_range(start, end, freq="D")
        for day in days:
            daily_records.append({
                "date": day,
                "rainfall_mm": row["rainfall_mm"],
            })

    rain_daily = pd.DataFrame(daily_records).set_index("date")
    rain_daily = rain_daily.reindex(wide_df.index).ffill().fillna(0)
    return rain_daily
```

### 4.4 Combine All Exogenous Into Unified Builder

```python
def build_all_exog(
    wide_df: pd.DataFrame,
    national_df: pd.DataFrame,
) -> pd.DataFrame:
    """Unified exogenous builder: Fourier + price rolling + weather + rainfall."""
    parts = [build_fourier_exog(wide_df.index)]

    # National price rolling features (leakage-safe)
    price_exog = build_national_price_exog(national_df, wide_df.index)
    if price_exog is not None and not price_exog.empty:
        parts.append(price_exog)

    # Weather features
    weather_exog = build_weather_exog(wide_df)
    if weather_exog is not None and not weather_exog.empty:
        parts.append(weather_exog)

    # Rainfall features
    rainfall_exog = build_rainfall_exog(wide_df)
    if rainfall_exog is not None and not rainfall_exog.empty:
        parts.append(rainfall_exog)

    combined = pd.concat(parts, axis=1)
    combined = combined.ffill().fillna(0)

    # Drop any constant columns (no predictive value, causes XGB warnings)
    nunique = combined.nunique()
    combined = combined.loc[:, nunique > 1]

    return combined
```

### 4.5 Update `train_xgboost()` to Use New Exog

Replace the `exog_all = build_fourier_exog(wide.index)` call in `process_commodity()` with:

```python
exog_all = build_all_exog(wide, national)
```

### 4.6 Update Prophet to Use Weather Regressors

```python
def train_prophet(national_train: pd.DataFrame, weather_exog: pd.DataFrame = None):
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

    # Add weather regressors if available
    if weather_exog is not None and not weather_exog.empty:
        aligned = weather_exog.reindex(pd.DatetimeIndex(national_train["ds"]))
        for col in aligned.columns:
            if aligned[col].nunique() > 1:
                df[col] = aligned[col].fillna(0).values
                m.add_regressor(col)

    m.fit(df)
    # ... rest of MAPE computation
```

### 4.7 Serving-Time Exog Strategy

> **This is the most critical architectural gap**: feature engineering at training time is only useful if the same features can be constructed at serve time for *future* dates. Fourier features are deterministic (no data needed). Weather/rainfall features are not — you can't have tomorrow's actual weather.

**Chosen approach: Climatological Normals + Open Meteo hybrid**

Build climatological normals once from the historical `weather_monthly_features.parquet`. Use Open Meteo 16-day forecast for near-term predictions; fall back to normals beyond day 16.

```python
# backend/app/ml/serving_exog.py

import json
from pathlib import Path
import pandas as pd
import numpy as np

# Built once at startup from weather_monthly_features.parquet
# Format: {month_int: {temp: float, humidity: float, rainfall: float}}
_CLIMATOLOGICAL_NORMALS: dict[int, dict] = {}

def _build_normals_from_parquet(parquet_path: Path) -> dict[int, dict]:
    """Compute 30-year monthly climate averages — used as deterministic future exog."""
    wdf = pd.read_parquet(parquet_path, engine="pyarrow")
    monthly = wdf.groupby("month").agg({
        "avg_temp_c":   "mean",
        "avg_humidity": "mean",
        "rainfall_mm":  "mean",
    })
    return {
        int(month): {
            "temp":     round(float(row["avg_temp_c"]), 2),
            "humidity": round(float(row["avg_humidity"]), 2),
            "rainfall": round(float(row["rainfall_mm"]), 2),
        }
        for month, row in monthly.iterrows()
    }

def load_climatological_normals():
    """Call once at app startup."""
    global _CLIMATOLOGICAL_NORMALS
    weather_path = Path(__file__).parents[3] / "data" / "features" / "weather_monthly_features.parquet"
    if weather_path.exists():
        _CLIMATOLOGICAL_NORMALS = _build_normals_from_parquet(weather_path)

def build_future_exog(start_date, horizon: int, use_open_meteo: bool = True) -> pd.DataFrame:
    """
    Build exog DataFrame for future prediction dates.

    Days 1-16:  Open Meteo 16-day forecast (if available and use_open_meteo=True)
    Days 17+:   Climatological normals (deterministic, no API dependency)

    The SAME columns must be present here as were used at training time.
    """
    future_index = pd.date_range(start=start_date, periods=horizon, freq="D")
    fourier = build_fourier_exog(future_index)  # Always deterministic

    climate_rows = []
    open_meteo_data = {}

    if use_open_meteo and _CLIMATOLOGICAL_NORMALS:
        try:
            # Reuse harvest_advisor's weather client (already in codebase)
            from app.harvest_advisor.weather_client import fetch_forecast
            forecast = fetch_forecast(days=min(16, horizon))
            open_meteo_data = {
                pd.Timestamp(r["date"]): r
                for r in forecast.get("daily", [])
            }
        except Exception:
            pass  # Graceful: fall through to normals only

    for d in future_index:
        if d in open_meteo_data:
            row = open_meteo_data[d]
            climate_rows.append({
                "weather_temp":     row.get("temperature_2m_mean", 25.0),
                "weather_humidity": row.get("relative_humidity_2m_mean", 70.0),
                "weather_rainfall": row.get("precipitation_sum", 0.0),
            })
        else:
            norm = _CLIMATOLOGICAL_NORMALS.get(d.month, {"temp": 25.0, "humidity": 70.0, "rainfall": 0.0})
            climate_rows.append({
                "weather_temp":     norm["temp"],
                "weather_humidity": norm["humidity"],
                "weather_rainfall": norm["rainfall"],
            })

    climate_df = pd.DataFrame(climate_rows, index=future_index)
    return pd.concat([fourier, climate_df], axis=1)
```

**Update `service.py` `_invoke_model()`**:

```python
# In ForecastService._invoke_model(), after loading models:
from app.ml.serving_exog import build_future_exog

future_exog = build_future_exog(
    start_date=date.today() + timedelta(days=1),
    horizon=horizon,
)

# Align columns to what was used at training time (stored in meta)
train_exog_columns = meta.get("exog_columns", [])
if train_exog_columns:
    future_exog = future_exog.reindex(columns=train_exog_columns, fill_value=0)

xgb_pred = xgb_forecaster.predict(steps=horizon, exog=future_exog, levels=[district])
```

**Store exog column schema in meta during training**:

```python
# At end of train_forecast_v4.py process_commodity():
meta["exog_columns"] = list(exog_all.columns)
```

**Call `load_climatological_normals()` in `app/main.py` lifespan**:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.ml.serving_exog import load_climatological_normals
    load_climatological_normals()
    yield
```

---

## 5. Phase 3 — Commodity Tiering & Adaptive Training

### 5.1 Define Tiers

```python
COMMODITY_TIERS = {
    "A": {  # High-data: ≥50 districts, ≥5 years daily data
        "strategy": "full_ensemble",
        "target_r2": 0.80,
        "xgb_config": {"n_estimators": 600, "max_depth": 8, "learning_rate": 0.02},
    },
    "B": {  # Medium-data: 10–49 districts
        "strategy": "full_ensemble",
        "target_r2": 0.65,
        "xgb_config": {"n_estimators": 400, "max_depth": 6, "learning_rate": 0.03},
    },
    "C": {  # Low-data: <10 districts
        "strategy": "prophet_only",
        "target_r2": 0.50,
        "xgb_config": None,  # Skip XGBoost, Prophet-only
    },
    "D": {  # Minimal: <730 days of data
        "strategy": "seasonal_average",
        "target_r2": None,  # Historical average only
        "xgb_config": None,
    },
}
```

### 5.2 Auto-Classify Commodities

Add to `process_commodity()`:

```python
def classify_commodity(df: pd.DataFrame, national: pd.DataFrame) -> str:
    """Assign commodity to tier based on data quality."""
    n_districts = df["district"].nunique()
    n_days = len(national)

    if n_days < MIN_DAYS:
        return "D"
    if n_districts < 10:
        return "C"
    if n_districts >= 50:
        return "A"
    return "B"
```

### 5.3 Skip XGBoost for Tier C/D

In `process_commodity()`:

```python
tier = classify_commodity(df, national)
tier_config = COMMODITY_TIERS[tier]

if tier_config["strategy"] == "seasonal_average":
    # Save seasonal average only, no model training
    save_seasonal_fallback(slug, national)
    return True

if tier_config["strategy"] == "prophet_only":
    # Train Prophet only, skip XGBoost entirely
    prophet_model, prophet_mape = train_prophet(national_train)
    alpha = 1.0  # 100% Prophet
    xgb_forecaster = None
    xgb_mape = None
else:
    # Full ensemble
    xgb_config = tier_config["xgb_config"]
    # ... train both
```

### 5.4 Expected Tier Distribution (Estimated)

| Tier | Count | Strategy | Expected R² |
|------|-------|----------|-------------|
| A | ~30 | Full ensemble + tuning | 0.80–0.92 |
| B | ~100 | Full ensemble, default config | 0.60–0.80 |
| C | ~80 | Prophet-only | 0.40–0.65 |
| D | ~46 | Seasonal average (no model) | N/A |

---

## 6. Phase 4 — Hyperparameter Tuning

### 6.1 Category-Based XGBoost Configs

```python
CROP_CATEGORY_CONFIGS = {
    "vegetables": {
        # High volatility, short cycles
        "n_estimators": 600,
        "max_depth": 8,
        "learning_rate": 0.02,
        "subsample": 0.7,
        "lags": [1, 3, 7, 14, 30, 91],  # Include 1-day and 3-day lags
    },
    "food_grains": {
        # Low volatility, strong annual seasonality
        "n_estimators": 300,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "pulses": {
        # Moderate volatility
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "oilseeds": {
        # Influenced by global commodity markets
        "n_estimators": 500,
        "max_depth": 7,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "spices": {
        # Highly volatile, thin markets
        "n_estimators": 300,
        "max_depth": 4,  # Regularize more — sparse data
        "learning_rate": 0.05,
        "subsample": 0.7,
        "lags": [7, 14, 30, 91],
    },
    "fruits": {
        # Highly seasonal (perennial crops)
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "lags": [7, 14, 30, 91, 182, 365],
    },
    "default": {
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "lags": [7, 14, 30, 91, 182, 365],
    },
}
```

### 6.2 Commodity-To-Category Mapping With Auto-Classification Fallback

The explicit name map covers ~50/256 commodities. For the remaining ~200, auto-classify using the `category_id` field already present in the parquet (inspect once to build the ID→type map).

```python
# Explicit name-based map (high-confidence overrides)
COMMODITY_CATEGORY_MAP = {
    # Vegetables
    "onion": "vegetables", "tomato": "vegetables", "potato": "vegetables",
    "brinjal": "vegetables", "cauliflower": "vegetables", "cabbage": "vegetables",
    "carrot": "vegetables", "green chilli": "vegetables", "lady finger": "vegetables",
    # Food grains
    "rice": "food_grains", "wheat": "food_grains", "maize": "food_grains",
    "bajra": "food_grains", "jowar": "food_grains", "barley": "food_grains",
    # Pulses
    "arhar (tur/red gram)": "pulses", "moong": "pulses", "urad": "pulses",
    "gram (chana)": "pulses", "lentil (masur)": "pulses",
    # Oilseeds
    "groundnut": "oilseeds", "mustard": "oilseeds", "soybean": "oilseeds",
    "sunflower": "oilseeds",
    # Spices
    "turmeric": "spices", "chilli red": "spices", "coriander": "spices",
    "cumin": "spices", "ginger": "spices",
    # Fruits
    "mango": "fruits", "banana": "fruits", "apple": "fruits",
    "grapes": "fruits", "orange": "fruits",
}

# Agmarknet category_id → crop type (build from: df['category_id'].value_counts())
# Inspect parquet once to verify these IDs match your dataset
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

def get_xgb_config(commodity: str, category_id: int = None) -> dict:
    """
    Resolve XGBoost config by commodity name first, then category_id fallback.
    Logs a warning for commodities resolved only by category_id so the explicit
    map can be extended over time.
    """
    # 1. Try slug-normalized name lookup
    normalized = commodity.lower().strip()
    category = COMMODITY_CATEGORY_MAP.get(normalized)

    # 2. Auto-classify from parquet category_id
    if not category and category_id is not None:
        category = CATEGORY_ID_TO_CROP_TYPE.get(int(category_id))
        if category:
            print(f"  [AUTO-CLASSIFY] '{commodity}' → '{category}' via category_id={category_id}")

    # 3. Hard fallback
    if not category:
        print(f"  [UNCATEGORIZED] '{commodity}' — using default config. Add to COMMODITY_CATEGORY_MAP.")
        category = "default"

    return CROP_CATEGORY_CONFIGS.get(category, CROP_CATEGORY_CONFIGS["default"])
```

**Update `process_commodity()`** to pass `category_id`:

```python
# Extract category_id from first row of commodity DataFrame
category_id = df["category_id"].iloc[0] if "category_id" in df.columns else None
xgb_config = get_xgb_config(commodity, category_id=category_id)
```

### 6.3 Update `train_xgboost()` to Accept Config

```python
def train_xgboost(wide_train, exog_train, config: dict):
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
    lags = config.get("lags", LAGS)
    forecaster = ForecasterRecursiveMultiSeries(regressor=xgb, lags=lags)
    forecaster.fit(series=wide_train, exog=exog_train)
    return forecaster
```

---

## 7. Phase 5 — Prophet Improvements

### 7.1 Category-Based Prophet Configs

```python
PROPHET_CONFIGS = {
    "vegetables": {
        "changepoint_prior_scale": 0.15,  # More flexible for volatile prices
        "seasonality_prior_scale": 5,
        "n_changepoints": 40,
        "seasonality_mode": "multiplicative",  # Better for proportional swings
    },
    "food_grains": {
        "changepoint_prior_scale": 0.03,  # Conservative for stable prices
        "seasonality_prior_scale": 15,
        "n_changepoints": 20,
        "seasonality_mode": "additive",
    },
    "spices": {
        "changepoint_prior_scale": 0.20,  # Very flexible
        "seasonality_prior_scale": 3,
        "n_changepoints": 50,
        "seasonality_mode": "multiplicative",
    },
    "default": {
        "changepoint_prior_scale": 0.05,
        "seasonality_prior_scale": 10,
        "n_changepoints": 25,
        "seasonality_mode": "additive",
    },
}
```

### 7.2 Update `train_prophet()` to Use Category Config

```python
def train_prophet(national_train, prophet_config: dict, weather_exog=None):
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=prophet_config["changepoint_prior_scale"],
        seasonality_prior_scale=prophet_config["seasonality_prior_scale"],
        n_changepoints=prophet_config["n_changepoints"],
        seasonality_mode=prophet_config.get("seasonality_mode", "additive"),
    )
    # ... rest of function
```

### 7.3 Add Custom Seasonalities

For commodities with known seasonal patterns (monsoon, harvest):

```python
# For all crops — add Indian monsoon seasonality
m.add_seasonality(name="monsoon", period=365.25/3, fourier_order=3)

# For Rabi/Kharif crops — add half-year seasonality
m.add_seasonality(name="crop_cycle", period=365.25/2, fourier_order=5)
```

---

## 8. Phase 6 — Ensemble & Evaluation Fixes

### 8.1 Fix R² Computation — Per-District Then Aggregate

**Problem**: Current code averages XGBoost predictions across districts then compares to national mean price → cross-district errors compound.

**Fix**: Compute R² per district, then take weighted median:

```python
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
    Returns (overall_r2, per_district_r2_dict).
    """
    # Prophet prediction (national line)
    future = national_test.copy()
    exog = build_fourier_exog(pd.DatetimeIndex(national_test["ds"]))
    for col in exog.columns:
        future[col] = exog[col].values
    prophet_pred = prophet_model.predict(future)["yhat"].values

    # XGBoost prediction (per district)
    # NOTE: column is 'level' (singular) — not 'levels'
    try:
        xgb_pred_df = xgb_forecaster.predict(steps=len(wide_test), exog=exog_test)
        if isinstance(xgb_pred_df.index, pd.MultiIndex):
            xgb_wide = xgb_pred_df["pred"].unstack(level="level")
        elif "level" in xgb_pred_df.columns:
            xgb_wide = xgb_pred_df.pivot_table(
                index=xgb_pred_df.index, columns="level", values="pred",
            )
        else:
            xgb_wide = xgb_pred_df
    except Exception:
        # If XGB fails, evaluate Prophet alone
        n = min(len(prophet_pred), len(national_test))
        y_true = national_test["y"].values[:n]
        r2 = float(sklearn_r2(y_true, prophet_pred[:n]))
        return r2, {"national_prophet_only": r2}

    # Per-district ensemble R²
    district_r2s = {}
    district_weights = {}
    for col in wide_test.columns:
        y_true = wide_test[col].dropna().values
        if col in xgb_wide.columns:
            y_xgb = xgb_wide[col].dropna().values
        else:
            continue
        n = min(len(y_true), len(y_xgb), len(prophet_pred))
        if n < 14:  # Need at least 2 weeks for meaningful R²
            continue
        ensemble = alpha * prophet_pred[:n] + (1 - alpha) * y_xgb[:n]
        try:
            r2 = float(sklearn_r2(y_true[:n], ensemble))
            district_r2s[col] = r2
            district_weights[col] = n  # Weight by data points
        except Exception:
            continue

    if not district_r2s:
        return 0.0, {}

    # Weighted median R²
    items = sorted(district_r2s.items(), key=lambda x: x[1])
    weights = [district_weights[k] for k, _ in items]
    values = [v for _, v in items]
    cumw = np.cumsum(weights) / np.sum(weights)
    median_idx = np.searchsorted(cumw, 0.5)
    overall_r2 = values[min(median_idx, len(values) - 1)]

    return overall_r2, district_r2s
```

### 8.2 Store Per-District Metrics in Meta

```python
meta = {
    "alpha": alpha,
    "r2_score": overall_r2,
    "r2_per_district": per_district_r2,  # NEW
    "prophet_mape": prophet_mape,
    "xgb_mape": xgb_mape,
    "tier": tier,                         # NEW
    "commodity_category": category,        # NEW
    "n_districts": len(districts_list),
    "last_data_date": last_data_date,
    "districts_list": districts_list,
    "exog_columns": list(exog_all.columns),  # NEW — required for serving-time alignment
    "interval_coverage_80pct": interval_coverage,  # NEW — see 8.4
    "trained_at": datetime.utcnow().isoformat(),
}
```

### 8.3 Add Walk-Forward Cross-Validation

Instead of a single train/test split, use expanding-window CV with 3 folds:

```python
def evaluate_with_walk_forward(
    national: pd.DataFrame,
    wide: pd.DataFrame,
    commodity_category: str,
    n_splits: int = 3,
) -> float:
    """
    Walk-forward CV: train on expanding window, evaluate on next 90 days.
    Returns median R² across folds — more robust than single-split evaluation.
    """
    xgb_config = get_xgb_config(commodity_category)
    prophet_config = PROPHET_CONFIGS.get(commodity_category, PROPHET_CONFIGS["default"])
    total_days = len(national)
    step = total_days // (n_splits + 1)
    r2_scores = []

    for i in range(n_splits):
        train_end = step * (i + 2)
        test_end = min(train_end + 90, total_days)
        if test_end - train_end < 14:
            continue

        nat_train = national.iloc[:train_end]
        nat_test  = national.iloc[train_end:test_end]
        w_train   = wide.iloc[:train_end]
        w_test    = wide.iloc[train_end:test_end]

        exog_train = build_all_exog(w_train, nat_train)
        exog_test  = build_all_exog(w_test, nat_test)

        # Critical: test exog must have SAME columns as train exog
        exog_test = exog_test.reindex(columns=exog_train.columns, fill_value=0)

        try:
            prophet_m, p_mape = train_prophet(nat_train, prophet_config)
            xgb_f = train_xgboost(w_train, exog_train, xgb_config)
            xgb_mape = compute_xgb_mape(xgb_f, w_test, exog_test)
            alpha = max(0.1, min(0.9, compute_alpha(p_mape, xgb_mape)))
            fold_r2, _ = compute_ensemble_r2_v2(
                prophet_m, xgb_f, nat_test, w_test, exog_test, alpha
            )
            r2_scores.append(fold_r2)
            print(f"  [CV fold {i+1}/{n_splits}] R²={fold_r2:.3f}")
        except Exception as e:
            print(f"  [WARN] CV fold {i+1} failed: {e}")

    if not r2_scores:
        return 0.0
    return float(np.median(r2_scores))
```

### 8.4 Prediction Interval Calibration

Prophet outputs `yhat_lower`/`yhat_upper` as 80% uncertainty intervals, but these are often poorly calibrated for agricultural commodity prices. Measure actual coverage on the test set and apply a correction factor at serve time.

```python
def calibrate_intervals(
    prophet_model,
    national_test: pd.DataFrame,
) -> float:
    """
    Returns empirical coverage of Prophet's 80% interval on held-out test data.
    Well-calibrated model: ~0.80. Below 0.60 → widen intervals at serve time.
    """
    future = national_test.copy()
    forecast = prophet_model.predict(future)

    actual = national_test["y"].values
    lower  = forecast["yhat_lower"].values
    upper  = forecast["yhat_upper"].values
    n = min(len(actual), len(lower))

    in_interval = np.mean((actual[:n] >= lower[:n]) & (actual[:n] <= upper[:n]))
    return float(in_interval)

# Store in meta:
meta["interval_coverage_80pct"] = calibrate_intervals(prophet_model, national_test_df)
```

**At serve time in `service.py`** — apply correction if undercoverage:

```python
coverage = meta.get("interval_coverage_80pct", 0.80)
if coverage < 0.70 and coverage > 0:
    correction = 0.80 / coverage  # Widen proportionally
    mid   = point.price_mid
    low   = mid - (mid - point.price_low)  * correction
    high  = mid + (point.price_high - mid) * correction
    point = point.model_copy(update={"price_low": round(low, 2), "price_high": round(high, 2)})
```

---

## 9. Phase 7 — Confidence Gating in Serving Layer

### 9.1 Explicit Graceful Degradation Hierarchy

`service.py` must attempt each level in order before falling to the next. The `tier_label` returned to the UI must reflect the actual source so farmers understand the forecast quality.

```
Fallback chain (attempt in order):
  Level 1: Full Ensemble       R² ≥ 0.5, tier A/B    → confidence: Green/Yellow
  Level 2: Prophet-only        R² ≥ 0.3, tier C       → confidence: Yellow
  Level 3: Seasonal stats      {slug}_seasonal.json   → confidence: Yellow,  tier_label="seasonal_average"
  Level 4: National avg        parquet national mean  → confidence: Red,     tier_label="national_average"
  Level 5: 404                 no data at all         → HTTP 404
```

### 9.2 Add Quality Gate to `ForecastService`

**File**: `backend/app/forecast/service.py`

Add to `_invoke_model()`:

```python
# After loading meta:
meta = load_meta(slug)
r2 = meta.get("r2_score", 0.0) if meta else 0.0
tier = meta.get("tier", "D") if meta else "D"

# Quality gate — route to appropriate fallback level
if r2 < 0.3 or tier == "D":
    return self._seasonal_fallback(commodity, district, horizon)

if r2 < 0.5:
    # Use model but label as "low confidence"
    confidence_colour = "Red"
    tier_label = "low_confidence_model"
```

### 9.3 Implement Seasonal Fallback

```python
def _seasonal_fallback(
    self, commodity: str, district: str, horizon: int,
) -> ForecastResponse:
    """Return seasonal historical average when model quality is insufficient."""
    from app.ml.seasonal.aggregator import get_monthly_stats

    stats = get_monthly_stats(commodity)
    if not stats:
        return self._national_average_fallback(commodity, district, horizon)

    today = date.today()
    points = []
    for d in range(1, horizon + 1):
        forecast_date = today + timedelta(days=d)
        month = forecast_date.month
        month_stats = stats.get(month, {})
        mid = month_stats.get("median", month_stats.get("mean", 0))
        low = month_stats.get("p25", mid * 0.9)
        high = month_stats.get("p75", mid * 1.1)
        points.append(ForecastPoint(
            date=str(forecast_date),
            price_low=round(low, 2),
            price_mid=round(mid, 2),
            price_high=round(high, 2),
        ))

    return ForecastResponse(
        commodity=commodity,
        district=district,
        horizon_days=horizon,
        direction="flat",
        price_low=points[0].price_low if points else None,
        price_mid=points[0].price_mid if points else None,
        price_high=points[0].price_high if points else None,
        confidence_colour="Yellow",
        tier_label="seasonal_average",
        last_data_date=None,
        forecast_points=points,
        r2_score=None,
    )

def _national_average_fallback(
    self, commodity: str, district: str, horizon: int,
) -> ForecastResponse:
    """Last resort: national historical mean. Always returns something."""
    # Query national mean price from DB or parquet
    # ...
    return ForecastResponse(
        # ...
        confidence_colour="Red",
        tier_label="national_average",
    )
```

### 9.4 Update Confidence Colour Logic

Replace MAPE-only logic with R²-gated assessment:

```python
def compute_confidence_colour(r2: float, mape: float) -> str:
    """Combined R² + MAPE confidence assessment."""
    if r2 >= 0.75 and mape < 0.12:
        return "Green"
    if r2 >= 0.50 and mape < 0.25:
        return "Yellow"
    return "Red"
```

---

## 10. Phase 8 — Yield Model Fixes

### 10.1 Current State

The yield models (`train_yield_model.py`) have proper guards:
- Temporal hold-out (last 3 years)
- R² > 0 gate before saving
- Overfitting gap tracking

### 10.2 Fix KNN Imputation for Soil Features

Currently uses `fillna(median)`. Soil features (N, P, K, pH) have spatial correlation — neighbouring districts have similar soil profiles. KNN imputation preserves this:

```python
from sklearn.impute import KNNImputer

SOIL_FEATURES = ["N_kg_ha", "P_kg_ha", "K_kg_ha", "pH", "OC_pct", "EC_dS_m"]
WEATHER_FEATURES = ["avg_temp_c", "avg_humidity", "rainfall_mm"]
FEATURE_COLS = SOIL_FEATURES + WEATHER_FEATURES + ["area_ha"]

def impute_soil_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    KNN imputation (k=5, distance-weighted) for soil features.
    Preserves spatial correlation better than median fill.
    Only applied to SOIL_FEATURES — weather features use forward-fill.
    """
    imputer = KNNImputer(n_neighbors=5, weights="distance")
    df = df.copy()
    df[SOIL_FEATURES] = imputer.fit_transform(df[SOIL_FEATURES])
    df[WEATHER_FEATURES] = df[WEATHER_FEATURES].ffill().fillna(0)
    return df
```

### 10.3 Add Per-Crop Models for High-Data Crops

Currently only vegetables get per-crop RF models. Extend to major food crops:

```python
HIGH_DATA_CROPS = [
    "rice", "wheat", "maize", "cotton", "onion", "potato", "tomato",
    "sugarcane", "groundnut", "soybean",
]

def train_per_crop_model(
    df: pd.DataFrame,
    crop: str,
) -> tuple[RandomForestRegressor | None, float]:
    """
    Train individual RF model for high-data crops.
    Saves as yield_rf_{slug}.joblib if R² > 0 on hold-out.
    """
    crop_df = df[df["crop_name"].str.lower() == crop.lower()].copy()
    if len(crop_df) < 50:
        print(f"  [SKIP] {crop}: only {len(crop_df)} rows — need ≥50")
        return None, 0.0

    crop_df = impute_soil_features(crop_df)

    # Temporal split: last 3 years as test (avoids data leakage)
    split_year = crop_df["year"].max() - 3
    train = crop_df[crop_df["year"] <= split_year]
    test  = crop_df[crop_df["year"] >  split_year]

    if len(train) < 30 or len(test) < 10:
        print(f"  [SKIP] {crop}: insufficient train ({len(train)}) or test ({len(test)}) rows")
        return None, 0.0

    X_train, y_train = train[FEATURE_COLS], train["yield_kg_ha"]
    X_test,  y_test  = test[FEATURE_COLS],  test["yield_kg_ha"]

    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    train_r2 = r2_score(y_train, rf.predict(X_train))
    test_r2  = r2_score(y_test,  rf.predict(X_test))
    overfit_gap = train_r2 - test_r2

    print(f"  {crop}: train_R²={train_r2:.3f}, test_R²={test_r2:.3f}, gap={overfit_gap:.3f}")

    if test_r2 <= 0:
        print(f"  [SKIP] {crop}: test R²={test_r2:.3f} — not saving")
        return None, test_r2

    if overfit_gap > 0.4:
        print(f"  [WARN] {crop}: high overfit gap ({overfit_gap:.3f}) — model may not generalise")

    out_path = ARTIFACTS_DIR / f"yield_rf_{slugify(crop)}.joblib"
    joblib.dump(rf, out_path)
    print(f"  [SAVED] {out_path.name} (test R²={test_r2:.3f})")
    return rf, test_r2

# In train_yield_model.py main():
for crop in HIGH_DATA_CROPS:
    train_per_crop_model(df, crop)
```

### 10.4 Feature Importance Validation

After training each model, log feature importances to confirm weather/soil features are contributing:

```python
def log_feature_importance(model: RandomForestRegressor, crop: str):
    importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
    top5 = importances.nlargest(5)
    print(f"  Top features for {crop}:")
    for feat, imp in top5.items():
        print(f"    {feat}: {imp:.3f}")
    # Flag if soil features are all near-zero (suggests imputation failed)
    soil_importance = importances[SOIL_FEATURES].sum()
    if soil_importance < 0.05:
        print(f"  [WARN] {crop}: soil features contribute only {soil_importance:.1%} — check imputation")
```

---

## 11. Phase 9 — Retraining Pipeline & CI

### 11.1 Create Unified Training Script

Create `backend/scripts/train_all.py`:

```python
"""
Unified training orchestrator.

Usage:
    cd backend
    python -m scripts.train_all                    # Train everything
    python -m scripts.train_all --price-only       # Only price forecasts
    python -m scripts.train_all --yield-only       # Only yield models
    python -m scripts.train_all --force             # Retrain even if exists
    python -m scripts.train_all --commodity onion   # Single commodity
    python -m scripts.train_all --workers 4         # Parallel workers
"""

import argparse
from scripts.train_forecast_v4 import main as train_prices
from scripts.train_yield_model import main as train_yields
from scripts.train_seasonal import main as train_seasonal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-only", action="store_true")
    parser.add_argument("--yield-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--commodity", type=str, default=None)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    if not args.yield_only:
        print("=" * 60)
        print("PHASE 1: Price Forecast Models")
        print("=" * 60)
        train_prices(force=args.force, commodity=args.commodity, workers=args.workers)

    if not args.price_only:
        print("=" * 60)
        print("PHASE 2: Yield Prediction Models")
        print("=" * 60)
        train_yields()

        print("=" * 60)
        print("PHASE 3: Seasonal Calendars")
        print("=" * 60)
        train_seasonal()

    print("\nAll training complete.")
```

### 11.2 Parallelization Implementation

Sequential training of 256 commodities can take 8–12 hours. Use `multiprocessing.Pool` to run 4 commodities in parallel, cutting wall-clock time to ~2–3 hours.

```python
# In train_forecast_v4.py

from multiprocessing import Pool, cpu_count
import logging

# Use logging (not print) inside worker functions — print output garbles in multiprocessing
logger = logging.getLogger("train_forecast_v4")

def main(force: bool = False, commodity: str = None, workers: int = 4):
    commodities = get_all_commodities()
    if commodity:
        commodities = [c for c in commodities if c == commodity]

    n_workers = min(workers, cpu_count(), len(commodities))
    logger.info(f"Training {len(commodities)} commodities with {n_workers} workers")

    # Prophet suppresses stdout by default but is noisy in multiprocessing.
    # Set suppress_stdout_stderrr=True in Prophet constructor inside workers.
    args = [(slug, force) for slug in commodities]

    with Pool(processes=n_workers) as pool:
        results = pool.starmap(process_commodity, args)

    successes  = sum(1 for r in results if r)
    failures   = len(results) - successes
    logger.info(f"Complete: {successes}/{len(commodities)} succeeded, {failures} failed")
    return successes, failures
```

> **Note**: Each worker loads the full parquet independently — pre-filter by commodity before spawning to reduce memory pressure. Each worker uses ~1.5 GB RAM; 4 workers = ~6 GB required.

### 11.3 Training Report Generator

After training, generate a JSON report:

```python
def generate_training_report():
    """Scan all _meta.json files and produce a quality report."""
    report = {
        "total_commodities": 0,
        "tier_distribution": {"A": 0, "B": 0, "C": 0, "D": 0},
        "r2_distribution": {"excellent": 0, "good": 0, "fair": 0, "poor": 0},
        "failed": [],
        "top_performers": [],
        "worst_performers": [],
        "uncategorized": [],  # Commodities that fell through to "default" config
    }
    # ... scan artifacts and populate
    return report
```

### 11.4 Define `train_seasonal`

`train_seasonal` is referenced by `train_all.py`. Create `backend/scripts/train_seasonal.py`:

```python
"""
Compute per-commodity monthly price statistics from the Agmarknet parquet.
Writes ml/artifacts/{slug}_seasonal.json — used by the seasonal fallback
in ForecastService when model quality is insufficient.

Output format per commodity:
{
  "1": {"mean": 2400, "median": 2350, "p10": 1800, "p25": 2100, "p75": 2700, "p90": 3100},
  "2": { ... },
  ...  # months 1–12
}
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from app.ml.loader import slugify

PARQUET_PATH  = Path(__file__).parents[2] / "agmarknet_daily_10yr.parquet"
ARTIFACTS_DIR = Path(__file__).parents[2] / "ml" / "artifacts"


def build_seasonal_stats(df: pd.DataFrame) -> dict:
    """Monthly price stats from historical data."""
    df = df.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.month
    result = {}
    for month, grp in df.groupby("month"):
        prices = grp["price_modal"].dropna()
        prices = prices[prices > 0]
        if len(prices) < 10:
            continue
        result[str(int(month))] = {
            "mean":   round(float(prices.mean()), 2),
            "median": round(float(prices.median()), 2),
            "p10":    round(float(prices.quantile(0.10)), 2),
            "p25":    round(float(prices.quantile(0.25)), 2),
            "p75":    round(float(prices.quantile(0.75)), 2),
            "p90":    round(float(prices.quantile(0.90)), 2),
        }
    return result


def main():
    print("Loading parquet...")
    parquet = pd.read_parquet(PARQUET_PATH, engine="pyarrow", columns=["date", "commodity", "price_modal"])

    saved = 0
    skipped = 0
    for commodity, grp in parquet.groupby("commodity"):
        stats = build_seasonal_stats(grp)
        if not stats:
            skipped += 1
            continue
        slug = slugify(commodity)
        out = ARTIFACTS_DIR / f"{slug}_seasonal.json"
        out.write_text(json.dumps(stats, indent=2))
        saved += 1
        print(f"  [OK] {commodity} ({slug}) — {len(stats)} months")

    print(f"\nSeasonal calendars: {saved} saved, {skipped} skipped (insufficient data)")


if __name__ == "__main__":
    main()
```

### 11.5 Automated Retraining Schedule

Add to `docker-compose.prod.yml` or cron:

```yaml
  ml-retrain:
    build: ./backend
    command: python -m scripts.train_all --force --workers 4
    environment:
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./ml/artifacts:/app/ml/artifacts
      - ./data:/app/data
    profiles: ["retrain"]
    # Run weekly: docker compose --profile retrain up ml-retrain
```

---

## 12. Phase 10 — Monitoring & Drift Detection

### 12.1 Add Drift Detection Endpoint

**File**: `backend/app/forecast/routes.py`

```python
@router.get("/forecasts/model-health")
def model_health():
    """Return health metrics for all trained models."""
    from app.ml.loader import list_commodity_slugs, load_meta
    results = []
    for slug in list_commodity_slugs():
        meta = load_meta(slug)
        if not meta:
            continue
        results.append({
            "commodity": slug,
            "r2_score": meta.get("r2_score", 0),
            "tier": meta.get("tier", "unknown"),
            "prophet_mape": meta.get("prophet_mape"),
            "xgb_mape": meta.get("xgb_mape"),
            "interval_coverage_80pct": meta.get("interval_coverage_80pct"),
            "last_data_date": meta.get("last_data_date"),
            "trained_at": meta.get("trained_at"),
            "needs_retrain": _needs_retrain(meta),
        })
    return {"models": results, "total": len(results)}
```

### 12.2 Staleness Detection

```python
from datetime import datetime, timedelta

def _needs_retrain(meta: dict) -> bool:
    trained_at = meta.get("trained_at")
    if not trained_at:
        return True
    age = datetime.utcnow() - datetime.fromisoformat(trained_at)
    if age > timedelta(days=30):
        return True
    if meta.get("r2_score", 0) < 0.3:
        return True
    if meta.get("interval_coverage_80pct", 1.0) < 0.50:
        return True  # Intervals are severely miscalibrated
    return False
```

---

## 13. Implementation Order & Timeline

| Phase | Description | Depends On | Est. Hours | Priority |
|-------|-------------|------------|------------|----------|
| **1** | Critical bug fixes (MAPE, alpha, force-retrain, pandas deprecations) | — | 4 | **P0** |
| **6** | R² evaluation fix (per-district) + interval calibration | Phase 1 | 4 | **P0** |
| **3** | Commodity tiering | — | 3 | **P0** |
| **7** | Confidence gating + graceful degradation hierarchy | Phase 6 | 5 | **P0** |
| **2** | Feature engineering + serving-time exog strategy | Phase 1 | 10 | **P1** |
| **4** | Hyperparameter tuning + auto-classification | Phase 3 | 4 | **P1** |
| **5** | Prophet improvements | Phase 4 | 3 | **P1** |
| **9.4** | train_seasonal script | — | 2 | **P1** |
| **8** | Yield model fixes (KNN imputation + per-crop models) | — | 6 | **P2** |
| **9** | Retraining pipeline + parallelization | Phases 1–7 | 5 | **P2** |
| **10** | Monitoring & drift detection | Phase 9 | 3 | **P3** |

**Total estimated: ~49 hours**

### Recommended Execution Order

```
Week 1 (P0 — Stop the bleeding):
  Day 1: Phase 1 (bug fixes + pandas deprecations) + Phase 6 (R² fix + calibration)
  Day 2: Phase 3 (tiering) + Phase 7 (graceful degradation hierarchy)
  Day 3: Retrain ALL models with fixes → verify improvement

Week 2 (P1 — Accuracy improvements):
  Day 4:   Phase 9.4 (train_seasonal — required for fallback chain)
  Day 4-5: Phase 2 (feature engineering + serving-time exog)
  Day 6:   Phase 4 (hyperparameter tuning + auto-classification)
  Day 7:   Phase 5 (Prophet tuning)
  Day 8:   Full retrain → measure R² improvements

Week 3 (P2 — Infrastructure):
  Day 9:  Phase 8 (yield models: KNN imputation + per-crop)
  Day 10: Phase 9 (retraining pipeline + parallelization)
  Day 11: Phase 10 (monitoring)
```

---

## 14. Success Metrics

### After Phase 1+6+7 (Bug Fixes + Gating):

| Metric | Before | Target |
|--------|--------|--------|
| Commodities with R² ≥ 0.5 | 5/256 | 30+/256 |
| Commodities served with broken models | 248 | 0 |
| Users receiving "Red" confidence for bad models | 0% | 100% |
| Serving requests hitting correct fallback level | unknown | tracked |

### After Phase 2+4+5 (Features + Tuning):

| Metric | Before | Target |
|--------|--------|--------|
| Tier A commodities with R² ≥ 0.8 | 3/256 | 25+/30 |
| Tier B commodities with R² ≥ 0.6 | 0/256 | 60+/100 |
| Tier C commodities with R² ≥ 0.4 | 0/256 | 50+/80 |
| Overall median R² | -0.996 | 0.55+ |
| 80% interval coverage (calibration) | unknown | ≥ 0.70 |

### After Full Pipeline (All Phases):

| Metric | Target |
|--------|--------|
| Tier A median R² | 0.82 |
| Tier B median R² | 0.65 |
| Tier C median R² | 0.48 |
| Model staleness (days since retrain) | < 30 |
| API requests hitting seasonal fallback | < 20% |
| "Green" confidence forecasts actually accurate (MAPE < 12%) | > 90% |
| Interval calibration (80% intervals covering 80% of actuals) | > 0.72 |
| Commodities auto-classified via category_id (not "default") | > 90% |
| Training wall-clock time (256 commodities, 4 workers) | < 3 hrs |

---

## 15. Risk Log

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Weather/rainfall parquet files missing | Medium | Phase 2 partially blocked | `build_all_exog()` gracefully skips missing sources; Fourier-only training still runs |
| Open Meteo unavailable at serve time | Low | Phase 4.7 degraded | `build_future_exog()` falls back to climatological normals transparently |
| skforecast API changes in future updates | Low | Training breaks | Pin `skforecast==0.20.1` in requirements.txt |
| Commodity category mapping incomplete | Low | Mitigated by category_id auto-classification | Log `[UNCATEGORIZED]` warnings; review after first retrain |
| Retraining takes >6 hours | Low | Delays deployment | 4-worker parallelization targets ~2–3 hrs; use `--commodity` flag for spot fixes |
| Tier C Prophet-only models still underperform | Medium | Some commodities stuck at R² < 0.4 | Accept; graceful fallback chain ensures seasonal_average is served instead |
| Memory issues with 4 parallel workers | Medium | OOM on 8GB machines | Pre-filter parquet by commodity before spawning workers; use `--workers 2` on small machines |
| Interval calibration < 0.50 for volatile crops | Medium | Misleading price bands | Correction factor in service.py widens bands; flag in model-health endpoint |
| `exog_columns` mismatch between training and serving | Low | XGBoost predict() fails | Stored in meta + reindex at serve time handles this; caught by integration tests |

---

## Appendix A: Files to Modify

| File | Changes |
|------|---------|
| `backend/scripts/train_forecast_v3.py` | Bug fixes, feature integration, tiering, CLI args **(OR create train_forecast_v4.py — see Appendix B)** |
| `backend/app/forecast/service.py` | Confidence gating, graceful degradation hierarchy, interval calibration, future exog |
| `backend/app/ml/loader.py` | No changes needed |
| `backend/app/ml/price_features.py` | No changes needed |
| `backend/app/ml/rainfall_features.py` | No changes needed |
| `backend/app/ml/weather_features.py` | No changes needed |
| `backend/app/ml/soil_features.py` | No changes needed (not used for price forecasting) |
| `backend/scripts/train_yield_model.py` | KNN imputation, per-crop models for HIGH_DATA_CROPS |
| `backend/app/forecast/routes.py` | Add `/forecasts/model-health` endpoint |
| `backend/app/main.py` | Call `load_climatological_normals()` in lifespan |
| **NEW**: `backend/app/ml/serving_exog.py` | Climatological normals + Open Meteo hybrid for future-date exog |
| **NEW**: `backend/scripts/train_all.py` | Unified training orchestrator with parallelization |
| **NEW**: `backend/scripts/train_seasonal.py` | Seasonal calendar builder (monthly price stats) |

## Appendix B: Recommended Approach — Create `train_forecast_v4.py`

Rather than modifying `train_forecast_v3.py` (which produced all current artifacts), create a **new** `train_forecast_v4.py` that incorporates ALL fixes. This allows:

1. **A/B comparison**: Run v3 and v4 side by side on a subset of commodities
2. **Safe rollback**: If v4 produces worse results for a commodity, v3 artifacts remain intact
3. **Clean code**: No need to work around the existing bugs in-place

### Artifact Versioning Strategy

```
v3 artifacts (current):  ml/artifacts/{slug}_prophet.joblib
                         ml/artifacts/{slug}_xgboost.joblib
                         ml/artifacts/{slug}_meta.json

v4 artifacts (new):      ml/artifacts/v4/{slug}_prophet.joblib
                         ml/artifacts/v4/{slug}_xgboost.joblib
                         ml/artifacts/v4/{slug}_meta.json
                         ml/artifacts/v4/{slug}_seasonal.json  ← new
```

**`loader.py` loading order** (update `load_meta()` and model loaders):

```python
def load_meta(slug: str) -> dict | None:
    """Prefer v4 artifacts; fall back to v3 for backward compatibility."""
    v4_path = ARTIFACTS_DIR / "v4" / f"{slug}_meta.json"
    v3_path = ARTIFACTS_DIR / f"{slug}_meta.json"
    for path in [v4_path, v3_path]:
        if path.exists():
            return json.loads(path.read_text())
    return None
```

**Migration path**:
1. Train v4 commodity-by-commodity, verifying improvement
2. Once v4 coverage reaches 100% with R² ≥ v3 for ≥ 90% of commodities, promote v4 to default
3. Delete root-level v3 `.joblib` files (keep `_meta.json` for audit trail)
4. Remove the v4 subdirectory prefix from `loader.py`
