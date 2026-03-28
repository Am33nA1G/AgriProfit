# Phase 4: XGBoost Forecasting + Serving - Research

**Researched:** 2026-03-02
**Domain:** Time-series ML forecasting with skforecast + XGBoost, FastAPI ML serving, PostgreSQL forecast cache, APScheduler, Recharts UI
**Confidence:** HIGH (core stack verified via official docs and PyPI; patterns verified against existing codebase)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FORE-01 | One XGBoost model per commodity using ForecasterRecursiveMultiSeries, trained on pairs with >= 730 days data | skforecast 0.20.1 ForecasterRecursiveMultiSeries + XGBRegressor 3.2.0; wide-format DataFrame input per commodity |
| FORE-02 | 4-fold walk-forward validation, RMSE and MAPE logged per fold to model_training_log before model file written | backtesting_forecaster_multiseries with TimeSeriesFold(n_splits=4); metrics returned as DataFrame, logged to new table |
| FORE-03 | 7-day and 14-day forecast for any commodity+district with sufficient data | predict_interval(steps=14) returns low/mid/high bands; steps=7 for 7-day variant |
| FORE-04 | Response includes direction (up/down/flat), predicted range, confidence colour, tier label | Derived from predict_interval output; direction = sign(mid[-1] - mid[0]), confidence mapped from MAPE |
| FORE-05 | Pairs with < 365 days data routed to seasonal calendar fallback, not ML forecast | Pre-filter at training time: skip pairs below threshold; at serve time: query coverage_days from price_history |
| FORE-06 | Forecast results cached in forecast_cache PostgreSQL table, refreshed nightly via APScheduler | New table with JSONB payload; APScheduler CronTrigger(hour=3) job added alongside existing price sync |
| SERV-01 | FastAPI endpoint /api/v1/forecast/{commodity}/{district} | New router registered in main.py; same pattern as existing transport router |
| SERV-02 | Trained models stored in ml/artifacts/, loaded at startup into app.state.models | joblib.dump to ml/artifacts/{commodity}.joblib; lifespan hook loads index; lazy per-model loading |
| SERV-03 | LRU cache with configurable memory limit, lazy-loaded on first request | cachetools.LRUCache(maxsize=N) in app.state; loaded via get_or_load_model() on demand |
| SERV-04 | APScheduler nightly forecast refresh job at 03:00 | CronTrigger(hour=3) job regenerates stale entries in forecast_cache; extends existing scheduler.py |
| UI-02 | Price forecast page — commodity + district selector, 14-day chart with confidence band, tier label | Next.js page; Recharts ComposedChart with Line (mid) + Area (low-high band) already in frontend deps |
| UI-05 | All dashboards display coverage gap messages when feature unavailable | tier label in API response drives conditional UI banner; no silent failure |
</phase_requirements>

---

## Summary

Phase 4 builds the XGBoost forecasting pipeline end-to-end: offline training, walk-forward validation logging, PostgreSQL cache, lazy-model serving, and a Next.js chart UI. The primary library is **skforecast 0.20.1** (released Feb 2026), which wraps **XGBoost 3.2.0** via scikit-learn's `XGBRegressor`. skforecast's `ForecasterRecursiveMultiSeries` trains one global model per commodity across all qualifying district series simultaneously, which is the correct pattern for the agricultural price domain where districts share commodity-level seasonality.

The serving layer introduces two new PostgreSQL tables (`model_training_log` and `forecast_cache`) and extends the existing APScheduler with a `CronTrigger(hour=3)` nightly job. Model files are persisted as joblib artifacts in `ml/artifacts/`. In-process model loading uses `cachetools.LRUCache` stored in `app.state.models` — lazy-loaded on first request, evicted when count exceeds configured limit. This avoids the startup-time penalty of loading hundreds of commodity models while providing bounded memory use.

The frontend uses **Recharts 3.7.0** (already in `package.json`) with a `ComposedChart` containing a `Line` (modal price history + mid forecast) and an `Area` (low-high confidence band). The tier label (`"full model"` vs `"seasonal average fallback"`) and direction (`up/down/flat`) are returned by the API and drive conditional UI rendering. No new charting libraries are needed.

**Primary recommendation:** Use skforecast 0.20.1 with XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05), lags=[7,14,30,90], and TimeSeriesFold(n_splits=4) for backtesting. Write models to `ml/artifacts/{commodity}.joblib` and serve from a `cachetools.LRUCache` in `app.state`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| skforecast | 0.20.1 (Feb 2026) | ForecasterRecursiveMultiSeries — multi-series recursive ML forecasting | Purpose-built for this exact pattern; wraps any sklearn-compatible regressor; built-in backtesting and prediction intervals |
| xgboost | 3.2.0 (Feb 2026) | XGBRegressor — gradient boosting regressor | Fastest sklearn-compatible GBM; proven for tabular price data; stable serialization via joblib |
| joblib | (stdlib in sklearn) | Model artifact serialization | More efficient than pickle for large numpy arrays; standard in sklearn ecosystem |
| cachetools | 7.0.1 | LRUCache for in-process model store | Thread-safe; maxsize limits count; getsizeof hook for byte-based limits if needed |
| APScheduler | 3.10.4 (already installed) | CronTrigger nightly forecast refresh | Already in codebase — extend existing scheduler.py, do not add new scheduler |
| SQLAlchemy | 2.0.46 (already installed) | ORM for model_training_log and forecast_cache tables | Already in codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scikit-learn | (skforecast dependency) | TimeSeriesFold for walk-forward CV splits | Required by skforecast — do not import sklearn.model_selection.TimeSeriesSplit separately |
| pandas | 2.2.3 (already installed) | Wide-format DataFrame for series input to ForecasterRecursiveMultiSeries | Already in codebase; correct version |
| pyarrow | 17.0.0 (already installed) | Parquet reading for training data | Already pinned to 17.0.0 — do NOT upgrade (19.0.0 incompatible with this parquet) |
| Recharts | 3.7.0 (already in frontend) | ComposedChart for price history + forecast overlay with confidence band | Already installed; use ComposedChart + Line + Area |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| skforecast ForecasterRecursiveMultiSeries | Custom recursive loop with sklearn | Hand-rolling walk-forward validation and recursive prediction is error-prone (leakage risk); skforecast handles edge cases |
| cachetools.LRUCache | functools.lru_cache | lru_cache cannot be cleared at runtime; cachetools allows explicit eviction and size inspection needed for memory management |
| joblib | pickle / xgboost native save | joblib is standard for sklearn pipelines; pickle is insecure from unknown sources; xgboost native format doesn't save the full skforecast wrapper |
| PostgreSQL forecast_cache table | Redis | No new infrastructure; Redis already optional in this project (not required) |
| APScheduler CronTrigger | Celery beat | APScheduler already installed and running; Celery is a heavyweight new dependency |

**Installation:**
```bash
pip install skforecast==0.20.1 xgboost==3.2.0 cachetools
```

---

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── ml/
│   ├── __init__.py
│   └── artifacts/           # joblib model files: {commodity_slug}.joblib
├── app/
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── features.py      # Phase 3 feature functions (cutoff_date enforced)
│   │   ├── loader.py        # get_or_load_model(), LRU cache, app.state.models
│   │   └── train_xgboost.py # Offline training script (not imported at runtime)
│   ├── forecast/
│   │   ├── __init__.py
│   │   ├── routes.py        # GET /api/v1/forecast/{commodity}/{district}
│   │   ├── schemas.py       # Pydantic response models
│   │   └── service.py       # ForecastService: cache lookup, model invoke, fallback
│   ├── models/
│   │   ├── model_training_log.py  # SQLAlchemy model for training log table
│   │   └── forecast_cache.py      # SQLAlchemy model for cache table
│   └── integrations/
│       └── scheduler.py     # EXTEND: add nightly forecast refresh job
└── alembic/versions/
    ├── {rev}_add_model_training_log.py
    └── {rev}_add_forecast_cache.py
```

**Key constraint:** The `ml/artifacts/` directory lives at repo root level (per ROADMAP: `ml/artifacts/`), not inside `backend/`. The training script runs as `python backend/scripts/train_xgboost.py` and writes to `ml/artifacts/`.

### Pattern 1: ForecasterRecursiveMultiSeries — Per-Commodity Global Model
**What:** One forecaster per commodity, trained on all district series simultaneously using wide-format DataFrame (columns = district names, rows = dates, values = modal prices)
**When to use:** Always — this is the locked architecture per FORE-01

```python
# Source: skforecast.org/0.18.0/api/forecasterrecursivemultiseries
from skforecast.recursive import ForecasterRecursiveMultiSeries
from xgboost import XGBRegressor

forecaster = ForecasterRecursiveMultiSeries(
    regressor=XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
    ),
    lags=[7, 14, 30, 90],           # price lag features in days
    encoding='ordinal',              # district identity as ordinal feature
    transformer_series=None,         # no scaling needed for tree models
)

# series: wide-format DataFrame, index=DatetimeIndex, columns=district names
# Only include series with >= 730 days of data
forecaster.fit(series=series_df)
```

**Important:** In skforecast >= 0.17.0, the input DataFrame MUST have a `DatetimeIndex` or `RangeIndex` — automatic index generation was removed. Ensure the price DataFrame index is set to `pd.DatetimeIndex` before fitting.

### Pattern 2: Walk-Forward Validation with TimeSeriesFold
**What:** 4-fold backtesting that measures RMSE and MAPE per fold before any model is accepted for serving
**When to use:** Every training run — no model enters `ml/artifacts/` without logged validation

```python
# Source: skforecast.org/0.19.1/user_guides/backtesting
from skforecast.model_selection import backtesting_forecaster_multiseries, TimeSeriesFold
from sklearn.metrics import mean_absolute_percentage_error
import numpy as np

cv = TimeSeriesFold(
    n_splits=4,
    steps=14,                        # predict 14 days per fold
    initial_train_size=int(len(series_df) * 0.7),
    refit=False,                     # single trained model across folds
    fixed_train_size=False,          # expanding window
)

metrics_df, predictions_df = backtesting_forecaster_multiseries(
    forecaster=forecaster,
    series=series_df,
    cv=cv,
    metric=['mean_squared_error', 'mean_absolute_percentage_error'],
    add_aggregated_metric=True,
    n_jobs='auto',
    verbose=False,
)

# metrics_df columns: levels (district names) + metric columns
# rows: one per fold, plus aggregated row if add_aggregated_metric=True
# RMSE = sqrt of mean_squared_error column
rmse_per_fold = np.sqrt(metrics_df['mean_squared_error'].values)
mape_per_fold = metrics_df['mean_absolute_percentage_error'].values
```

**Note:** `TimeSeriesFold` is in `skforecast.model_selection` in 0.14+. Do NOT use `sklearn.model_selection.TimeSeriesSplit` directly — skforecast's version integrates with `backtesting_forecaster_multiseries`.

### Pattern 3: Prediction Intervals for Low/Mid/High Response
**What:** `predict_interval()` returns lower bound, point forecast, upper bound for confidence band
**When to use:** At serve time after cache miss

```python
# Source: skforecast.org/0.14.0/user_guides/probabilistic-forecasting.html
# Returns DataFrame: columns = [level, lower_bound, pred, upper_bound]
# level = district name
predictions = forecaster.predict_interval(
    steps=14,
    levels=["Tamil Nadu_Namakkal"],  # specific district series
    interval=[10, 90],               # 80% prediction interval
    n_boot=100,                      # bootstrap samples for interval
)

# Map to API response:
low = predictions['lower_bound'].iloc[-1]    # day 14 lower
mid = predictions['pred'].iloc[-1]           # day 14 point estimate
high = predictions['upper_bound'].iloc[-1]   # day 14 upper

# Direction: compare first vs last mid forecast
direction = "up" if mid > predictions['pred'].iloc[0] * 1.02 else \
            "down" if mid < predictions['pred'].iloc[0] * 0.98 else "flat"
```

### Pattern 4: LRU Model Cache in FastAPI app.state
**What:** Lazy-loaded per-commodity model store with configurable eviction
**When to use:** All serving — never load all models at startup

```python
# Source: cachetools docs + FastAPI app.state pattern
# In loader.py
import joblib
from cachetools import LRUCache
from pathlib import Path

ARTIFACTS_DIR = Path("ml/artifacts")
_model_cache: LRUCache = LRUCache(maxsize=50)  # max 50 models in memory

def get_or_load_model(commodity_slug: str):
    """Load model from cache or disk. Thread-safe via GIL for CPython."""
    if commodity_slug in _model_cache:
        return _model_cache[commodity_slug]

    artifact_path = ARTIFACTS_DIR / f"{commodity_slug}.joblib"
    if not artifact_path.exists():
        return None

    model = joblib.load(artifact_path)
    _model_cache[commodity_slug] = model
    return model

# In main.py lifespan: attach cache reference to app.state
# app.state.model_cache = _model_cache  (for monitoring/metrics)
```

**Thread safety note:** `cachetools.LRUCache` is NOT thread-safe by default. For multi-worker FastAPI (Uvicorn with multiple workers), use `threading.Lock`. For single-worker (typical dev/staging), GIL protects CPython dict operations.

### Pattern 5: forecast_cache Table Design
**What:** PostgreSQL table storing pre-computed forecast payloads, keyed by commodity+district+forecast_date
**When to use:** Every API response — serve from cache on hit, compute and write on miss

```python
# forecast_cache SQLAlchemy model (new)
# Unique key: (commodity_name, district_name, generated_date)
# payload: JSONB containing direction, low/mid/high, confidence_colour, tier_label, expires_at
# cache_hit performance target: <= 50ms (simple PK lookup on indexed text columns)
```

### Pattern 6: APScheduler Nightly Forecast Refresh
**What:** CronTrigger at 03:00 daily regenerates stale forecast_cache entries
**When to use:** Extend existing `scheduler.py` — add second job, do not create new scheduler instance

```python
# Source: APScheduler 3.x docs
from apscheduler.triggers.cron import CronTrigger

scheduler.add_job(
    refresh_forecast_cache_job,
    trigger=CronTrigger(hour=3, minute=0),
    id="refresh_forecast_cache",
    name="Nightly Forecast Cache Refresh",
    replace_existing=True,
)
```

### Pattern 7: Model Training Log Before Artifact Write
**What:** Every validation run inserts a row to `model_training_log` BEFORE writing the joblib file. If insert fails, file is not written.
**When to use:** Always — enforces the "no model without logged validation" invariant

```python
# Pseudocode for train_xgboost.py gate pattern
validation_results = run_walk_forward_validation(forecaster, series_df)
log_training_result(db, commodity, validation_results)  # raises on DB error
joblib.dump(forecaster, artifact_path)                  # only reached if log succeeds
```

### Anti-Patterns to Avoid
- **Load all models at startup:** Hundreds of commodities would consume gigabytes at startup; use lazy loading
- **Use sklearn TimeSeriesSplit directly:** Incompatible with `backtesting_forecaster_multiseries` — use skforecast's `TimeSeriesFold`
- **Point estimate only:** FORE-04 requires range (low/mid/high); always use `predict_interval()` not `predict()`
- **pickle for artifact persistence:** Use joblib — pickle is not safe for artifacts shared across environments
- **RangeIndex on series DataFrame:** skforecast >= 0.17.0 requires DatetimeIndex — always set `series_df.index = pd.DatetimeIndex(dates)`
- **Blocking model load inside async FastAPI handler:** joblib.load is CPU-bound I/O; if async handler is needed, run in threadpool via `asyncio.get_event_loop().run_in_executor(None, get_or_load_model, slug)`
- **Running APScheduler.start() twice:** The existing `start_scheduler()` in `integrations/scheduler.py` must be EXTENDED (add new job to same scheduler), not duplicated

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recursive multi-step forecasting | Custom for-loop calling predict() | skforecast ForecasterRecursiveMultiSeries | Error-prone recursive prediction; leakage risk in manual feature construction; edge cases in multi-series alignment |
| Walk-forward validation | Manual train/test splits | skforecast TimeSeriesFold + backtesting_forecaster_multiseries | Correct fold management, no leakage, returns metrics DataFrame ready to log |
| Prediction intervals | Percentile of residuals | skforecast predict_interval(n_boot=100) | Bootstrap intervals account for model uncertainty; manual residual percentiles ignore compounding errors |
| LRU eviction logic | Custom dict with max size | cachetools.LRUCache | Thread-safe, correct LRU ordering, inspectable, well-tested |
| Model artifact versioning | Custom filename scheme | joblib + metadata dict alongside model | joblib handles numpy-heavy objects efficiently; version info in separate JSON sidecar |

**Key insight:** Time series forecasting has more footguns than almost any ML domain (leakage, non-stationarity, recursive error accumulation). Use skforecast exactly as documented — resist the urge to simplify by writing a custom loop.

---

## Common Pitfalls

### Pitfall 1: Look-Ahead Leakage in Feature Construction
**What goes wrong:** Including future price data in lag features, inflating validation metrics
**Why it happens:** Pandas shift() off-by-one errors; incorrectly applying cutoff_date
**How to avoid:** Phase 3's feature functions use strict cutoff_date parameter — pass `cutoff_date=fold_end_date` when building features for each fold. skforecast's built-in lag construction handles this correctly when using `ForecasterRecursiveMultiSeries.fit()` — do NOT pre-compute lags and pass as exog
**Warning signs:** Walk-forward RMSE dramatically better than out-of-sample single-step accuracy

### Pitfall 2: skforecast Module Path Changes Across Versions
**What goes wrong:** Import errors because module structure changed in 0.14.0
**Why it happens:** Package was reorganized (0.14.0): `forecasting` module split into `recursive`, `direct`, `deep_learning`
**How to avoid:** Use these imports for 0.18+:
```python
from skforecast.recursive import ForecasterRecursiveMultiSeries
from skforecast.model_selection import backtesting_forecaster_multiseries, TimeSeriesFold
```
Do NOT use `from skforecast.forecasting import ...` (old API, < 0.14)
**Warning signs:** `ModuleNotFoundError: No module named 'skforecast.forecasting'`

### Pitfall 3: DatetimeIndex Requirement (skforecast >= 0.17.0)
**What goes wrong:** `ValueError` on `forecaster.fit()` when series has RangeIndex
**Why it happens:** skforecast 0.17.0 removed automatic index generation
**How to avoid:** Always convert before fitting:
```python
series_df.index = pd.to_datetime(series_df.index)
series_df.index.freq = pd.infer_freq(series_df.index)  # set freq if needed
```
**Warning signs:** `ValueError: Input series must have DatetimeIndex or RangeIndex`

### Pitfall 4: Forecast Cache <= 50ms Requirement
**What goes wrong:** Cache lookup exceeds 50ms target if commodity/district columns are unindexed
**Why it happens:** Text column lookup without B-tree index on (commodity_name, district_name, generated_date)
**How to avoid:** Add composite index in Alembic migration:
```python
Index('idx_forecast_cache_lookup', 'commodity_name', 'district_name', 'generated_date', unique=True)
```
**Warning signs:** Cache queries > 50ms even with small dataset

### Pitfall 5: Memory Pressure from LRU Cache
**What goes wrong:** Application OOM if many large commodity models are loaded simultaneously
**Why it happens:** LRU maxsize is count-based by default; a skforecast model with 90d lags over 500 districts may be 100-500MB
**How to avoid:** Start with maxsize=20 (configurable via settings). Monitor with `len(app.state.model_cache)`. Consider getsizeof-based sizing for byte limits if needed
**Warning signs:** uvicorn worker restarts, OOM kills in production

### Pitfall 6: Training on Insufficient Data Pairs (< 730 days)
**What goes wrong:** ForecasterRecursiveMultiSeries fails or produces garbage predictions for sparse series
**Why it happens:** Lags of [7,14,30,90] days require at least 90 days just to construct first feature row; walk-forward validation needs substantially more
**How to avoid:** Filter STRICTLY: only include district series with >= 730 days (FORE-01) in the wide-format DataFrame. Log excluded pairs with reason="insufficient_data" in model_training_log. At serve time, check coverage before calling model
**Warning signs:** Validation RMSE = NaN, model.fit() with empty DataFrame columns

### Pitfall 7: Alembic Multiple Heads
**What goes wrong:** `alembic upgrade head` fails with "multiple head revisions"
**Why it happens:** Two migration files both down_revision pointing to same parent (already happened in this project per MEMORY.md: a2b3c4d5e6f7 road_distance_cache)
**How to avoid:** Always check current head before writing new migration:
```bash
alembic heads  # should show single head
```
Set `down_revision` of new migration to the current head
**Warning signs:** `CommandError: Multiple head revisions are present`

### Pitfall 8: APScheduler Job Duplication at Startup
**What goes wrong:** Every app restart adds another "refresh_forecast_cache" job; jobs accumulate
**Why it happens:** Scheduler uses in-memory job store by default; `replace_existing=True` not set
**How to avoid:** Always use `id="refresh_forecast_cache"` AND `replace_existing=True` in `add_job()`
**Warning signs:** Multiple simultaneous forecast refresh jobs firing at 03:00

---

## Code Examples

Verified patterns from official sources:

### Complete Training Script Skeleton (train_xgboost.py)
```python
# Pattern verified against skforecast 0.18+ docs and PyPI
import sys
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy.orm import Session
from skforecast.recursive import ForecasterRecursiveMultiSeries
from skforecast.model_selection import backtesting_forecaster_multiseries, TimeSeriesFold
from xgboost import XGBRegressor

ARTIFACTS_DIR = Path("ml/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
MIN_DAYS_TRAIN = 730      # FORE-01
MIN_DAYS_SERVE = 365      # FORE-05

def build_series_df(db: Session, commodity: str) -> pd.DataFrame:
    """Wide-format DataFrame: DatetimeIndex, columns=district names, values=modal_price."""
    # Query price_history; join district_name_map for canonical names
    # Filter to >= MIN_DAYS_TRAIN per district
    # Pivot: rows=date, cols=district_canonical_name
    # Set index to DatetimeIndex
    ...

def train_commodity(commodity: str, series_df: pd.DataFrame, db: Session) -> None:
    forecaster = ForecasterRecursiveMultiSeries(
        regressor=XGBRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42,
        ),
        lags=[7, 14, 30, 90],
        encoding='ordinal',
    )

    # Walk-forward validation BEFORE fitting final model
    cv = TimeSeriesFold(
        n_splits=4,
        steps=14,
        initial_train_size=int(len(series_df) * 0.7),
        refit=False,
        fixed_train_size=False,
    )
    metrics_df, _ = backtesting_forecaster_multiseries(
        forecaster=forecaster,
        series=series_df,
        cv=cv,
        metric=['mean_squared_error', 'mean_absolute_percentage_error'],
        add_aggregated_metric=True,
        n_jobs='auto',
    )

    # Log validation metrics to DB (raises on failure — model NOT written if log fails)
    rmse_values = np.sqrt(metrics_df['mean_squared_error'].values)
    mape_values = metrics_df['mean_absolute_percentage_error'].values
    log_training(db, commodity, rmse_values, mape_values)

    # Fit final model on full dataset
    forecaster.fit(series=series_df)

    # Persist artifact
    commodity_slug = commodity.lower().replace(" ", "_")
    joblib.dump(forecaster, ARTIFACTS_DIR / f"{commodity_slug}.joblib")
```

### Alembic Migration: model_training_log
```python
# Pattern: extends project's existing Alembic style (Integer PK, snake_case, now())
def upgrade() -> None:
    op.create_table(
        "model_training_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity", sa.String(200), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("n_series", sa.Integer(), nullable=False),    # districts included
        sa.Column("n_folds", sa.Integer(), nullable=False),
        sa.Column("rmse_fold_1", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_fold_2", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_fold_3", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_fold_4", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_mean", sa.Numeric(10, 4), nullable=False),
        sa.Column("mape_mean", sa.Numeric(10, 4), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("skforecast_version", sa.String(20), nullable=False),
        sa.Column("xgboost_version", sa.String(20), nullable=False),
        sa.Column("excluded_districts", sa.Text(), nullable=True),  # JSON list
    )
    op.create_index("idx_model_training_log_commodity",
                    "model_training_log", ["commodity"])
```

### Alembic Migration: forecast_cache
```python
def upgrade() -> None:
    op.create_table(
        "forecast_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity_name", sa.String(200), nullable=False),
        sa.Column("district_name", sa.String(200), nullable=False),
        sa.Column("generated_date", sa.Date(), nullable=False),
        sa.Column("forecast_horizon_days", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),     # up/down/flat
        sa.Column("price_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_mid", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_high", sa.Numeric(10, 2), nullable=True),
        sa.Column("confidence_colour", sa.String(10), nullable=False),  # Green/Yellow/Red
        sa.Column("tier_label", sa.String(30), nullable=False),    # full model / seasonal average fallback
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "idx_forecast_cache_lookup",
        "forecast_cache",
        ["commodity_name", "district_name", "generated_date"],
        unique=True,
    )
```

### FastAPI Forecast Endpoint (routes.py)
```python
# Source: FastAPI docs pattern; follows existing transport router structure
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.forecast.schemas import ForecastResponse
from app.forecast.service import ForecastService

router = APIRouter(prefix="/forecast", tags=["Forecast"])

@router.get("/{commodity}/{district}", response_model=ForecastResponse)
def get_forecast(
    commodity: str,
    district: str,
    horizon: int = 14,
    db: Session = Depends(get_db),
):
    """
    Returns direction, predicted range, confidence colour, and tier label.
    Served from forecast_cache (cache hit target: <= 50ms).
    Falls back to seasonal average for low-coverage districts.
    """
    service = ForecastService(db)
    return service.get_forecast(commodity, district, horizon)
```

**Note:** Use `def` not `async def` for the route handler if it calls `get_or_load_model()` (which does disk I/O via joblib). FastAPI runs `def` routes in a thread pool automatically. Avoid blocking calls inside `async def` — this was the OSRM issue documented in MEMORY.md.

### Recharts Forecast Chart (Next.js)
```tsx
// Source: Recharts 3.7.0 API; pattern from project's existing recharts usage
// ComposedChart: Line for price history + Area for confidence band
import {
  ComposedChart, Line, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

// data shape: [{ date: "2026-03-01", actual: 2400, low: 2200, mid: 2500, high: 2800 }, ...]
<ResponsiveContainer width="100%" height={350}>
  <ComposedChart data={chartData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="date" />
    <YAxis />
    <Tooltip />
    <Legend />
    {/* Confidence band: Area between low and high */}
    <Area type="monotone" dataKey="high" stroke="none" fill="#e0f2fe" fillOpacity={0.5} />
    <Area type="monotone" dataKey="low" stroke="none" fill="#ffffff" fillOpacity={1} />
    {/* Mid forecast line */}
    <Line type="monotone" dataKey="mid" stroke="#2563eb" strokeDasharray="5 5" dot={false} />
    {/* Historical actuals */}
    <Line type="monotone" dataKey="actual" stroke="#16a34a" dot={false} />
  </ComposedChart>
</ResponsiveContainer>
```

### Confidence Colour Mapping
```python
# Map MAPE to traffic-light confidence colour
def mape_to_confidence_colour(mape: float) -> str:
    """
    Green: MAPE < 10% — reliable forecast
    Yellow: MAPE 10-25% — moderate uncertainty
    Red: MAPE > 25% or no walk-forward validation record — high uncertainty
    """
    if mape is None:
        return "Red"
    if mape < 0.10:
        return "Green"
    elif mape < 0.25:
        return "Yellow"
    return "Red"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from skforecast.forecasting import ForecasterAutoReg` | `from skforecast.recursive import ForecasterRecursiveMultiSeries` | skforecast 0.14.0 (2024) | Old import path raises ModuleNotFoundError on 0.14+ |
| Manual TimeSeriesSplit from sklearn | `TimeSeriesFold` from skforecast.model_selection | skforecast 0.14.0 | TimeSeriesFold integrates correctly with backtesting_forecaster_multiseries |
| `store_in_sample_residuals=True` default | `store_in_sample_residuals=False` default | skforecast 0.15.0 | Must explicitly set True if using predict_interval with bootstrapped residuals |
| Automatic RangeIndex generation | Must provide DatetimeIndex explicitly | skforecast 0.17.0 | Training will fail with implicit integer index |
| `series_long_to_dict()` | `reshape_series_long_to_dict()` | skforecast 0.17.0 | Old function name raises AttributeError |
| XGBoost 1.x/2.x | XGBoost 3.2.0 (Feb 2026) | Feb 2026 | Full Python 3.13 support; JVM removed; sklearn API unchanged |

**Deprecated/outdated:**
- `ForecasterAutoreg`: Single-series only; replaced by `ForecasterRecursive` for new code
- `backtesting_forecaster()` with old signature: Use `TimeSeriesFold` cv parameter instead of `initial_train_size` directly — the old API still works in 0.18 but TimeSeriesFold is the current pattern
- `skforecast.forecasting` module: Removed in 0.14.0 — use `skforecast.recursive`

---

## Open Questions

1. **How many commodity-district pairs actually meet the 730-day training threshold?**
   - What we know: Price data spans 10 years (to 2025-10-30); 314 commodities; ~557+ price districts
   - What's unclear: Distribution of data density — some niche commodities may have very few districts with 730+ day continuous records; training set size may surprise
   - Recommendation: Run a coverage audit query in plan 04-01 Wave 0: `SELECT commodity, COUNT(DISTINCT district) as n_districts FROM price_history GROUP BY commodity HAVING MAX(price_date) - MIN(price_date) >= INTERVAL '730 days'`. Log this before committing to model scope.

2. **How to handle missing days (price holidays, market closures) in the time series?**
   - What we know: Agricultural price data has gaps (weekends, holidays, bad weather)
   - What's unclear: Whether skforecast requires contiguous DatetimeIndex or handles sparse series; what imputation strategy to use
   - Recommendation: Forward-fill (ffill) with a max 7-day fill limit before fitting. Do NOT interpolate — forward-fill preserves last known price, which is semantically correct for modal prices.

3. **Memory footprint of skforecast models per commodity**
   - What we know: Each model stores lags [7,14,30,90] plus XGBoost trees; more districts = larger internal data structures
   - What's unclear: Exact RAM per model at serving time (could be 10MB–500MB depending on commodity breadth)
   - Recommendation: Default LRU cache maxsize=20; add a config setting `ml_model_cache_size` to settings.py; log model size after joblib.dump and store in model_training_log

4. **Data freshness: price data ends 2025-10-30, current date 2026-03-02**
   - What we know: 4+ month gap means forecast starting points are historical, not current
   - What's unclear: Whether to forecast from last known date forward, or from current date (would require interpolation over the gap)
   - Recommendation: Forecast from last available price date in the series. Display `"Forecast from last data: {last_date}"` in the UI alongside the confidence band. This is honest and avoids imputing 4 months of prices.

---

## Validation Architecture

`workflow.nyquist_validation` is not set in `.planning/config.json` (key absent). Standard `workflow` keys present: research, plan_check, verifier, auto_advance. Treating as validation enabled for this phase given the existing pytest infrastructure is mature and the phase has clear testable behaviours.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/test_forecast*.py -x -q` |
| Full suite command | `cd backend && pytest tests/ -q --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FORE-01 | ForecasterRecursiveMultiSeries trains per commodity, excludes < 730-day pairs | unit | `pytest tests/test_ml_training.py::test_series_filter_threshold -x` | ❌ Wave 0 |
| FORE-02 | Walk-forward validation returns RMSE+MAPE per fold; model_training_log insert happens before artifact write | unit | `pytest tests/test_ml_training.py::test_walk_forward_logs_before_artifact -x` | ❌ Wave 0 |
| FORE-03 | /api/v1/forecast/{commodity}/{district} returns 7-day and 14-day responses | integration | `pytest tests/test_forecast_api.py::test_forecast_endpoint_14day -x` | ❌ Wave 0 |
| FORE-04 | Response includes direction, price_low/mid/high, confidence_colour, tier_label | unit | `pytest tests/test_forecast_service.py::test_response_schema_fields -x` | ❌ Wave 0 |
| FORE-05 | Districts with < 365 days return tier_label="seasonal average fallback" | unit | `pytest tests/test_forecast_service.py::test_low_coverage_fallback -x` | ❌ Wave 0 |
| FORE-06 | forecast_cache hit returns same payload; miss writes to DB | integration | `pytest tests/test_forecast_api.py::test_cache_hit_latency -x` | ❌ Wave 0 |
| SERV-01 | /api/v1/forecast/{commodity}/{district} endpoint registered and reachable | integration | `pytest tests/test_forecast_api.py::test_endpoint_registered -x` | ❌ Wave 0 |
| SERV-02 | ml/artifacts/{slug}.joblib loaded into app.state on first request | unit | `pytest tests/test_ml_loader.py::test_lazy_load_on_first_request -x` | ❌ Wave 0 |
| SERV-03 | LRU cache evicts oldest model when maxsize exceeded | unit | `pytest tests/test_ml_loader.py::test_lru_eviction -x` | ❌ Wave 0 |
| SERV-04 | APScheduler refresh_forecast_cache job registered with CronTrigger(hour=3) | unit | `pytest tests/test_scheduler.py::test_nightly_refresh_job_registered -x` | ❌ Wave 0 |
| UI-02 | Forecast page renders with ComposedChart; shows tier label and direction | manual-only | N/A — visual rendering, no headless test | - |
| UI-05 | Coverage gap banner shown when tier_label == "seasonal average fallback" | unit (frontend) | `cd frontend && npm test -- test_forecast_page` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_forecast*.py tests/test_ml_*.py -x -q`
- **Per wave merge:** `cd backend && pytest tests/ -q --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_ml_training.py` — covers FORE-01, FORE-02 (unit tests for training script functions; mock DB, mock skforecast)
- [ ] `backend/tests/test_ml_loader.py` — covers SERV-02, SERV-03 (unit tests for loader.py; mock joblib.load)
- [ ] `backend/tests/test_forecast_service.py` — covers FORE-04, FORE-05 (pure unit tests, no DB needed)
- [ ] `backend/tests/test_forecast_api.py` — covers FORE-03, FORE-06, SERV-01 (integration tests using existing conftest.py SQLite setup; mock ML model)
- [ ] `backend/tests/test_scheduler.py` — covers SERV-04 (verify job registration; mock APScheduler)
- [ ] `ml/artifacts/` directory — must exist before tests run; add `mkdir -p ml/artifacts` to conftest.py or Wave 0
- [ ] ML dependencies install: `pip install skforecast==0.20.1 xgboost==3.2.0 cachetools` — not in current requirements.txt

---

## Sources

### Primary (HIGH confidence)
- https://pypi.org/project/skforecast/ — version 0.20.1 confirmed (Feb 2026), Python >= 3.10 requirement
- https://pypi.org/project/xgboost/ — version 3.2.0 confirmed (Feb 2026), sklearn API confirmed
- https://skforecast.org/0.18.0/releases/releases — API changes in 0.14, 0.15, 0.17 confirmed (DatetimeIndex requirement, module rename, residuals default change)
- https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html — CronTrigger(hour=3) syntax, replace_existing pattern
- https://cachetools.readthedocs.io/en/stable/ — LRUCache maxsize, thread safety, getsizeof hook
- `backend/requirements.txt` — confirmed APScheduler 3.10.4, pandas 2.2.3, pyarrow 17.0.0 already installed
- `frontend/package.json` — confirmed recharts 3.7.0 already installed
- `backend/app/main.py` — confirmed existing lifespan pattern, existing scheduler integration point
- `backend/app/integrations/scheduler.py` — confirmed BackgroundScheduler usage, extension point
- `backend/pytest.ini` — confirmed pytest configuration and test patterns

### Secondary (MEDIUM confidence)
- https://skforecast.org/0.18.0/api/forecasterrecursivemultiseries — constructor parameters (regressor, lags, encoding, transformer_series) verified via WebFetch
- https://skforecast.org/0.19.1/user_guides/backtesting — backtesting_forecaster_multiseries, TimeSeriesFold, fold_stride parameter pattern
- https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html — joblib/pickle serialization guidance

### Tertiary (LOW confidence)
- backtesting_forecaster_multiseries exact return DataFrame column structure (metrics_df columns) — verified pattern but exact column names for 0.20.1 should be confirmed by running `print(metrics_df.columns)` in Wave 0 test
- XGBRegressor hyperparameters (n_estimators=200, max_depth=6, lr=0.05) — reasonable defaults from domain knowledge; should be tuned with grid search or optuna in a follow-up

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — skforecast 0.20.1 and XGBoost 3.2.0 versions confirmed on PyPI; existing deps (APScheduler, pandas, Recharts) verified in codebase
- Architecture: HIGH — ForecasterRecursiveMultiSeries pattern confirmed via official docs; caching and scheduler patterns directly verified against existing code
- Pitfalls: HIGH — API breaking changes (0.14, 0.15, 0.17) confirmed from official release notes; project-specific pitfalls (pyarrow version, async handler blocking) from MEMORY.md
- Validation architecture: MEDIUM — test structure is inferred from existing test patterns; exact metrics DataFrame columns should be empirically verified in Wave 0

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (skforecast and XGBoost are stable; 30-day window reasonable)
