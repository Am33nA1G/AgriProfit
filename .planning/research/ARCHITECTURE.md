# Architecture Patterns: ML Intelligence Layer on AgriProfit

**Domain:** ML layer added to existing FastAPI + PostgreSQL + Next.js monolith
**Researched:** 2026-03-01
**Confidence:** HIGH (grounded in existing codebase patterns + verified sources)

---

## Recommended Architecture

The ML layer slots into the existing monolith without requiring a new microservice. Training runs
offline (scripts + APScheduler); model artifacts live on disk; FastAPI loads them at startup;
forecasts are written to a PostgreSQL cache table; Next.js dashboards read from cache-backed API
endpoints. No Redis, no separate model server.

```
Training Layer (offline)            Serving Layer (online)
─────────────────────               ─────────────────────────────────────────
  backend/ml/                         FastAPI lifespan startup
  ├── training/                        └── load_all_models()  ←── disk read
  │   ├── train_xgboost.py                   │
  │   ├── train_lstm.py                      ▼
  │   └── train_seasonal.py          app.state.models
  │                                   ├── xgboost["onion_MH"]
  ├── features/                       ├── xgboost["tomato_KA"]
  │   ├── price_features.py           └── lstm["onion_volatile"]
  │   ├── rainfall_features.py               │
  │   └── soil_features.py                   ▼
  │                                  /api/v1/ml/forecast
  └── artifacts/                     /api/v1/ml/seasonal
      ├── xgboost/                   /api/v1/ml/soil-advice
      │   ├── onion_MH_v1.joblib     /api/v1/ml/arbitrage
      │   └── tomato_KA_v1.joblib           │
      ├── lstm/                              ▼
      │   └── onion_v1.pt            PostgreSQL: forecast_cache
      └── seasonal/                  (commodity_id, district_id,
          └── stats_v1.parquet        forecast_date, horizon_days,
                                      predicted_price, generated_at)
                                             │
                                             ▼
                                     Next.js dashboards
                                     (read cached forecasts via API)
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `backend/ml/training/` | Offline model training scripts. Read from parquet files. Write artifacts to `ml/artifacts/`. Never import FastAPI or ORM. | parquet files on disk, `ml/features/` |
| `backend/ml/features/` | Pure Python feature engineering. No I/O. Takes DataFrames in, returns feature DataFrames out. Called by both training scripts and serving layer. | Called by training scripts AND by serving API endpoints |
| `backend/ml/artifacts/` | Serialised model files on disk. Versioned by filename suffix (`_v1`, `_v2`). xgboost → joblib, LSTM → torch state_dict (.pt), seasonal stats → parquet | Read by training scripts (write) and app startup (read) |
| `app/ml/` | FastAPI-facing ML code. Routes, schemas, serving logic. Loads models from `ml/artifacts/` at startup. Reads features from DB on request. Writes results to `forecast_cache` table. | `app.state.models`, PostgreSQL DB, `backend/ml/features/` |
| `app/ml/loader.py` | Single place to load all artifacts from disk into `app.state.models`. Called once in lifespan startup. | `ml/artifacts/`, `app.state` |
| `app/models/forecast_cache.py` | SQLAlchemy model for `forecast_cache` table. Stores pre-computed forecasts with TTL expiry. Acts as persistent cache. | PostgreSQL |
| `app/models/seasonal_price_stats.py` | Aggregated monthly price statistics. Written by offline script, read by API. Replaces repeated 25M-row queries. | PostgreSQL |
| `app/models/district_name_map.py` | Cross-dataset district harmonisation lookup. Written once, read everywhere. | PostgreSQL |
| `app/models/soil_crop_suitability.py` | Block-level soil suitability precomputed scores. Written by offline script. | PostgreSQL |
| `app/integrations/scheduler.py` (existing) | Extend to add scheduled forecast refresh job. Add `refresh_forecasts_job()` alongside existing `sync_prices_job()`. | `app/ml/` serving layer |
| Next.js frontend | Displays dashboards. Reads from `/api/v1/ml/*` endpoints. No direct DB access. | FastAPI API |

---

## Data Flow

### Training Flow (offline, does not touch the API server)

```
parquet files (disk)
    │
    ▼
ml/training/train_xgboost.py
    │  reads parquet with pd.read_parquet()
    │  calls ml/features/price_features.py (pure functions)
    │  calls ml/features/rainfall_features.py
    │  trains XGBRegressor per commodity+district group
    │  evaluates on holdout (last 90 days)
    │  if RMSE improves → serialise artifact
    ▼
ml/artifacts/xgboost/onion_MH_v2.joblib
```

### Seasonal Calendar Flow (write once, query many)

```
parquet (25M rows, all history)
    │
    ▼
ml/training/train_seasonal.py
    │  GROUP BY commodity, district, month
    │  compute p10/p50/p90/CV across 10 years
    │  write results to PostgreSQL: seasonal_price_stats
    ▼
PostgreSQL: seasonal_price_stats
    │
    ▼
GET /api/v1/ml/seasonal?commodity_id=X&district_id=Y
```

### Serving Flow (online, per request)

```
GET /api/v1/ml/forecast?commodity_id=X&district_id=Y&horizon=30
    │
    ▼
app/ml/routes.py
    │  check forecast_cache table (WHERE commodity_id=X AND district_id=Y
    │                               AND horizon_days=30 AND generated_at > NOW()-1day)
    │
    ├── CACHE HIT → return cached row  (latency: ~5ms)
    │
    └── CACHE MISS
            │
            ▼
        app/ml/service.py
            │  load model from app.state.models[key]  (already in memory)
            │  query DB for recent price history (date filter: last 180 days)
            │  query DB for rainfall features (district match via district_name_map)
            │  assemble feature vector via ml/features/price_features.py
            │  model.predict(X)
            │  write result to forecast_cache
            ▼
        return ForecastResponse
```

### Arbitrage Flow

```
GET /api/v1/ml/arbitrage?commodity_id=X&state_id=Y
    │
    ▼
Query: SELECT mandi_name, price_modal FROM price_history
       WHERE commodity_id=X AND price_date >= NOW()-7days
       GROUP BY mandi_name
    │
    ▼
Compute: cross-mandi price spread, flag if spread > threshold (20%)
    │
    ▼
Return: sorted list of mandis with price differential + transport cost link
```

---

## Folder Structure Recommendation

The existing codebase organizes by domain (transport, analytics, auth, etc.). The ML layer follows
the same pattern but splits across two root directories because training code must not import FastAPI
and serving code must not run heavy training.

```
backend/
├── app/                        # FastAPI application (EXISTING)
│   ├── ml/                     # NEW: FastAPI-facing ML module
│   │   ├── __init__.py
│   │   ├── loader.py           # load_all_models() → app.state.models
│   │   ├── routes.py           # /forecast, /seasonal, /soil-advice, /arbitrage
│   │   ├── schemas.py          # Pydantic request/response models
│   │   └── service.py          # forecast logic using loaded models
│   │
│   ├── models/                 # EXTEND existing models directory
│   │   ├── district_name_map.py    # NEW
│   │   ├── seasonal_price_stats.py # NEW
│   │   ├── forecast_cache.py       # NEW
│   │   └── soil_crop_suitability.py # NEW
│   │
│   └── integrations/
│       └── scheduler.py        # EXTEND: add refresh_forecasts_job()
│
├── ml/                         # NEW: training-only code (no FastAPI imports)
│   ├── features/
│   │   ├── __init__.py
│   │   ├── price_features.py       # lag features, rolling stats, seasonality dummies
│   │   ├── rainfall_features.py    # monthly deficit/surplus → district
│   │   ├── weather_features.py     # temp/humidity for ~260 districts (tiered)
│   │   └── soil_features.py        # NPK/pH deficiency scores per block
│   │
│   ├── training/
│   │   ├── __init__.py
│   │   ├── train_seasonal.py       # aggregation → seasonal_price_stats table
│   │   ├── train_xgboost.py        # commodity+district XGBoost models
│   │   ├── train_lstm.py           # PyTorch LSTM for volatile commodities
│   │   └── evaluate_models.py      # holdout evaluation, RMSE/MAPE logging
│   │
│   ├── artifacts/              # Serialised model files (git-ignored, large)
│   │   ├── xgboost/
│   │   │   └── {commodity}_{district_code}_v{N}.joblib
│   │   ├── lstm/
│   │   │   └── {commodity}_v{N}.pt
│   │   └── seasonal/
│   │       └── stats_v{N}.parquet
│   │
│   └── scripts/               # ETL one-time scripts
│       ├── harmonise_districts.py   # write district_name_map table
│       └── seed_soil_suitability.py # write soil_crop_suitability table
│
└── scripts/                   # EXISTING scripts directory
    └── train_models.py        # CLI entry point: calls ml/training/*.py
```

**Rationale for split:** The `app/ml/` directory mirrors `app/transport/` — it is the serving layer,
registered in `main.py`, imports SQLAlchemy models and FastAPI dependencies. The `ml/` directory at
backend root is pure data science: pandas, scikit-learn, PyTorch, no web framework imports. This
separation prevents training dependencies from polluting the API process and keeps import times fast.

---

## Specific Architecture Decisions

### 1. Where Trained Models Live: Disk Files

**Decision:** Serialised files in `ml/artifacts/` loaded at FastAPI startup into `app.state.models`.

**Rationale:**
- The existing codebase has no object storage (S3, GCS). Adding one for v1 is over-engineering.
- joblib (scikit-learn / XGBoost) and `torch.save(state_dict)` (PyTorch) are the production-standard serialisation formats. HIGH confidence — verified against pytorch.org docs and joblib docs.
- Load once at startup via the existing lifespan pattern (`main.py` already does this for the scheduler). The lifespan event in `main.py` is the correct insertion point.
- Memory cost estimate: ~5-50 MB per XGBoost model depending on tree count. For 50 commodity+district combinations that is ~250–2500 MB. Start with high-CV commodities only (onion, tomato, potato) to stay under 500 MB.
- LSTM models loaded with `torch.load(path, map_location='cpu')` + `model.eval()`. One LSTM per volatile commodity.
- Model file naming convention: `{commodity_slug}_{district_code}_v{N}.joblib`. Loader reads all files matching pattern, resolves latest version per key.
- Do NOT store models in the PostgreSQL database as BLOBs. BLOB storage in PostgreSQL kills query performance and makes versioning painful.

### 2. Feature Engineering: Offline Batch for Training, Lightweight Online for Serving

**Decision:** Offline batch pipeline for training features; minimal stateless feature assembly for serving.

**Training features (offline):**
- Run `train_xgboost.py` against the parquet file (not the live DB). The parquet file covers 2015–2025 and is already on disk. This completely decouples training from the production DB — no read pressure during training.
- Feature set: price lags (7, 14, 30, 60 days), rolling mean/std (30/90 days), month-of-year dummies, calendar seasonality, rainfall deficit (monthly, lagged 1–3 months), weather features where available (tiered: 260/571 districts).
- Pure functions in `ml/features/price_features.py` — input is a pandas DataFrame, output is a feature DataFrame. No I/O, testable independently.

**Serving features (online):**
- At request time, query PostgreSQL for the last 180 days of price history for the (commodity, district) pair. This is a tiny, fast, date-filtered query (not a full-table scan).
- Assemble features using the same `price_features.py` functions.
- Rainfall and weather features for serving: pre-aggregated into `seasonal_price_stats` at training time. Do not re-read the full rainfall parquet at request time.

**Why not an online feature store?** This is v1. The request rate is low (farmers querying forecasts, not millisecond trading). PostgreSQL as the feature source is sufficient. A dedicated feature store (Feast, Hopsworks) adds operational complexity not justified here.

### 3. Training Triggers: Scripts First, APScheduler Later

**Decision:** Manual scripts now; extend APScheduler for scheduled refresh.

**Phase 1 (manual):**
- `python backend/scripts/train_models.py --commodity onion --retrain` — triggers offline training.
- This is the right starting point. Train once on historical data, validate against holdout, ship artifacts. No scheduler risk.

**Phase 2 (scheduled refresh):**
- Extend `app/integrations/scheduler.py` to add a second job: `refresh_forecasts_job()`.
- Runs on a `CronTrigger` (e.g., daily at 03:00 AM IST after price sync has run).
- Job does NOT retrain models (that is expensive). It re-runs inference on the current `forecast_cache` population using the already-loaded models to produce fresh 30-day windows as new price data arrives.
- Model retraining (full retrain from parquet) runs as a weekly/monthly manual script or a separate long-running APScheduler job with a `CronTrigger(day_of_week='sun')`.

**Sequence dependency:** `sync_prices_job` must run before `refresh_forecasts_job`. Implement with a 2-hour offset (sync at 01:00, refresh at 03:00) rather than explicit chaining. APScheduler supports `CronTrigger` for this.

### 4. Reading 25M Rows Without Blocking: Parquet First, Chunked DB Second

**Decision:** Use the parquet file for all training. Use chunked DB reads with server-side cursors only if parquet is unavailable or stale.

**Why parquet for training:**
- The parquet file (`agmarknet_daily_10yr.parquet`) already exists at the repo root and covers the full 10-year history. `pd.read_parquet()` on a 25M-row parquet file with pyarrow is column-selective and fast (~5-15 seconds for a filtered read).
- Reading from parquet does not touch the PostgreSQL server at all. Zero read pressure on the production DB during training.
- Parquet supports predicate pushdown: `pd.read_parquet(path, filters=[('commodity', '==', 'Onion')])` returns only matching rows without loading the full file into memory.

**If parquet is unavailable (incremental data after Oct 2025):**
- Use `engine.connect().execution_options(stream_results=True)` + `pd.read_sql(query, con, chunksize=50000)` to stream from PostgreSQL.
- Always include `WHERE price_date >= '2015-01-01' AND price_date <= '2025-10-30' AND commodity_id = X` to avoid full-table scans (25M rows = 60s+ without date filter, per existing project memory).
- Run training in a background thread (not the FastAPI async event loop) to avoid blocking requests. The existing `trigger_startup_sync()` pattern in `scheduler.py` shows the correct approach: `threading.Thread(target=run_training, daemon=True)`.

**What NOT to do:**
- Do not `pd.read_sql("SELECT * FROM price_history", db)` — this kills the API.
- Do not run XGBoost training inside an `async def` FastAPI endpoint — blocking the event loop freezes all requests.

### 5. Forecast Results: PostgreSQL LOGGED Table (Not Redis, Not In-Memory)

**Decision:** PostgreSQL `forecast_cache` table with a `generated_at` timestamp as the cache key freshness indicator.

**Schema:**
```sql
CREATE TABLE forecast_cache (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commodity_id UUID NOT NULL REFERENCES commodities(id),
    district_id  TEXT NOT NULL,          -- harmonised district key
    horizon_days INTEGER NOT NULL,        -- 7, 14, 30
    forecast_date DATE NOT NULL,
    predicted_price NUMERIC(10,2) NOT NULL,
    confidence_score NUMERIC(5,4),
    model_version TEXT NOT NULL,
    feature_snapshot JSONB,              -- features used (audit/debug)
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (commodity_id, district_id, horizon_days, forecast_date)
);
CREATE INDEX idx_forecast_cache_lookup
    ON forecast_cache (commodity_id, district_id, horizon_days, generated_at DESC);
```

**Invalidation strategy:** API endpoint checks `generated_at > NOW() - INTERVAL '24 hours'`. If stale, re-run inference and upsert. No background cleanup needed immediately; add a weekly `DELETE FROM forecast_cache WHERE generated_at < NOW() - INTERVAL '30 days'` job later.

**Why not Redis:**
- Adds a new infrastructure dependency. Redis latency gain (~0.5ms vs ~5ms for indexed PostgreSQL) is irrelevant for agricultural price forecasts which update daily, not per-millisecond.
- PostgreSQL LOGGED tables are crash-safe; Redis without persistence loses data on restart.
- The project constraint is "PostgreSQL only — no separate vector DB or feature store for v1."

**Why not in-memory dict at startup:**
- Models load at startup (they are large). Forecast results (thousands of commodity+district combos) cannot all be pre-computed at startup — the startup time would be unacceptable.
- PostgreSQL cache table survives server restarts. In-memory dict does not.

**In-memory exception:** The `seasonal_price_stats` table can be fully loaded into memory at startup (it is small — ~314 commodities × 571 districts × 12 months × ~5 stats = ~10M cells, but only a fraction exist). Load into a Python dict keyed by `(commodity_id, district_id, month)` for O(1) seasonal lookups. This is the same pattern the transport engine uses for `district_coords.json`.

### 6. Soil Advice: Precomputed Lookup Table, Not Live Model

**Decision:** `soil_crop_suitability` table populated by offline script, served as a lookup by the API.

Soil data (84,794 block records) does not change frequently. The crop suitability logic (NPK/pH thresholds per crop) is deterministic, not probabilistic. The right pattern is:
1. Run `ml/scripts/seed_soil_suitability.py` once to compute suitability scores and write to the DB.
2. API endpoint reads from `soil_crop_suitability` with `WHERE district_id = X` — fast indexed lookup.
3. Update when new soil health survey data arrives (every 3 years per NABARD survey cycles).

No ML model needed. A rule-based scoring function is more interpretable to farmers and agronomists.

---

## Component Communication Map

```
┌─────────────────────────────────────────────────────────────┐
│                   OFFLINE (not in API process)              │
│                                                             │
│  parquet files → ml/training/*.py → ml/artifacts/          │
│       │               │                                     │
│  PostgreSQL ←── ml/scripts/ (harmonise, seed)              │
└─────────────────────────────────────────────────────────────┘
                          │ artifacts on disk
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI PROCESS                           │
│                                                             │
│  lifespan startup                                           │
│    └── app/ml/loader.py → app.state.models (dict)          │
│                                                             │
│  Request path:                                              │
│  app/ml/routes.py                                           │
│    └── app/ml/service.py                                    │
│          ├── app.state.models[key].predict()                │
│          ├── ml/features/price_features.py (pure)          │
│          ├── PostgreSQL: price_history (last 180d)          │
│          ├── PostgreSQL: district_name_map (cache in dict)  │
│          └── PostgreSQL: forecast_cache (read/write)        │
│                                                             │
│  APScheduler (existing):                                    │
│    ├── sync_prices_job() [existing, runs 01:00]             │
│    └── refresh_forecasts_job() [NEW, runs 03:00]            │
│          └── calls app/ml/service.py batch refresh          │
└─────────────────────────────────────────────────────────────┘
                          │ REST API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   NEXT.JS FRONTEND                          │
│                                                             │
│  /ml/seasonal   → seasonal calendar dashboard              │
│  /ml/forecast   → price chart with forecast overlay        │
│  /ml/soil       → crop advisor UI                          │
│  /ml/arbitrage  → mandi differential table                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Patterns to Follow

### Pattern 1: Model Registry via State Dict

Load all models at startup; access by key in handlers.

```python
# app/ml/loader.py
import joblib
import torch
from pathlib import Path
from app.ml.lstm_model import LSTMPriceModel  # defines architecture

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "ml" / "artifacts"

def load_all_models() -> dict:
    """
    Load all serialised artifacts into memory.
    Returns a dict keyed by model identifier.
    Called once during FastAPI lifespan startup.
    """
    models = {}
    # XGBoost models
    for path in sorted((ARTIFACTS_DIR / "xgboost").glob("*.joblib")):
        key = path.stem  # e.g. "onion_MH_v1"
        models[key] = joblib.load(path)

    # LSTM models
    for path in sorted((ARTIFACTS_DIR / "lstm").glob("*.pt")):
        key = path.stem
        architecture = LSTMPriceModel(input_size=20, hidden_size=64, num_layers=2)
        architecture.load_state_dict(torch.load(path, map_location="cpu"))
        architecture.eval()
        models[key] = architecture

    return models
```

```python
# app/main.py lifespan extension
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing scheduler startup ...
    from app.ml.loader import load_all_models
    app.state.models = load_all_models()
    yield
    # ... existing shutdown ...
```

### Pattern 2: Pure Feature Functions (No I/O)

Feature engineering functions take DataFrames in, return DataFrames out. Same code path for training and serving.

```python
# ml/features/price_features.py
import pandas as pd
import numpy as np

def add_lag_features(df: pd.DataFrame, lags: list[int]) -> pd.DataFrame:
    """
    Add price lag features. df must have columns: price_date, price_modal (sorted asc).
    Returns new DataFrame with added lag columns. Never mutates input.
    """
    result = df.copy()
    for lag in lags:
        result[f"price_lag_{lag}d"] = result["price_modal"].shift(lag)
    return result


def add_rolling_features(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    """Rolling mean and std. Returns new DataFrame."""
    result = df.copy()
    for window in windows:
        result[f"price_roll_mean_{window}d"] = (
            result["price_modal"].rolling(window, min_periods=1).mean()
        )
        result[f"price_roll_std_{window}d"] = (
            result["price_modal"].rolling(window, min_periods=1).std().fillna(0)
        )
    return result
```

### Pattern 3: Forecast Cache Upsert

```python
# app/ml/service.py
from sqlalchemy.dialects.postgresql import insert as pg_insert

def upsert_forecast(db: Session, forecast: dict) -> None:
    """Write or refresh a forecast result in the cache table."""
    stmt = pg_insert(ForecastCache).values(**forecast)
    stmt = stmt.on_conflict_do_update(
        index_elements=["commodity_id", "district_id", "horizon_days", "forecast_date"],
        set_={
            "predicted_price": stmt.excluded.predicted_price,
            "confidence_score": stmt.excluded.confidence_score,
            "model_version": stmt.excluded.model_version,
            "generated_at": stmt.excluded.generated_at,
        }
    )
    db.execute(stmt)
    db.commit()
```

### Pattern 4: Parquet Training Read with Column Filtering

```python
# ml/training/train_xgboost.py
import pandas as pd
from pathlib import Path

PARQUET_PATH = Path(__file__).parent.parent.parent.parent / "agmarknet_daily_10yr.parquet"
REQUIRED_COLUMNS = ["date", "commodity", "district", "state", "price_modal"]

def load_training_data(commodity: str, state: str) -> pd.DataFrame:
    """
    Load price data for one commodity+state from parquet.
    Uses predicate pushdown — does not load all 25M rows into memory.
    """
    return pd.read_parquet(
        PARQUET_PATH,
        columns=REQUIRED_COLUMNS,
        filters=[
            ("commodity", "==", commodity),
            ("state", "==", state),
        ]
    )
```

### Pattern 5: Scheduled Forecast Refresh (APScheduler Extension)

```python
# app/integrations/scheduler.py — extend existing file

def refresh_forecasts_job() -> None:
    """
    Re-run inference for all (commodity, district) pairs with stale forecasts.
    Runs in background thread — never called from async context.
    """
    logger.info("Starting scheduled forecast refresh...")
    from app.ml.service import refresh_all_forecasts
    from app.database.session import SessionLocal
    with SessionLocal() as db:
        count = refresh_all_forecasts(db)
    logger.info(f"Forecast refresh complete: {count} records updated")


def start_scheduler() -> BackgroundScheduler:
    # ... existing sync job ...
    scheduler.add_job(
        refresh_forecasts_job,
        trigger=CronTrigger(hour=3, minute=0),  # 03:00 daily
        id="refresh_forecasts",
        name="Refresh ML Forecasts",
        replace_existing=True,
    )
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running Training Inside FastAPI Endpoint

**What:** `POST /admin/retrain` that calls `model.fit(X_train, y_train)` synchronously.
**Why bad:** XGBoost training on 1M+ rows blocks the event loop for minutes. All other API requests freeze. The async event loop cannot yield during CPU-bound work.
**Instead:** Trigger training via `threading.Thread(target=train_fn)` or as an APScheduler job. The existing `trigger_startup_sync()` in `scheduler.py` demonstrates the correct pattern.

### Anti-Pattern 2: Full-Table Scan During Serving Feature Assembly

**What:** `SELECT * FROM price_history WHERE commodity_id = X` without a date filter.
**Why bad:** 25M rows. Documented in project memory as causing 60s+ timeouts.
**Instead:** Always `WHERE commodity_id = X AND price_date >= NOW() - INTERVAL '180 days'`. The serving layer only needs recent history for lag features, not the full 10-year archive.

### Anti-Pattern 3: One Model File for All Commodities

**What:** Train a single XGBoost model with commodity as a categorical feature.
**Why bad:** Onion (CV=34%) and Wheat (CV=2%) have completely different volatility profiles and seasonal patterns. A single model averages them, harming accuracy for both. The model also becomes a single point of failure — a training bug affects all commodities.
**Instead:** One model file per (commodity, state/district). This is more files but each is independently trainable, validatable, and replaceable.

### Anti-Pattern 4: Storing Models as PostgreSQL BLOBs

**What:** `INSERT INTO model_registry (name, blob) VALUES ('onion_v1', pg_read_binary_file(...))`.
**Why bad:** Pulling a 50MB joblib blob out of PostgreSQL on startup causes a large DB query. Model versioning via SQL rows is fragile. Binary BLOBs cannot be git-tracked or diff-inspected.
**Instead:** Files on disk in `ml/artifacts/`. Version via filename suffix. Git-ignore the directory (add to `.gitignore`). In production, copy artifacts alongside the app deployment.

### Anti-Pattern 5: LSTM for All Commodities

**What:** Train PyTorch LSTM for every commodity because it sounds more impressive.
**Why bad:** LSTM needs long sequences (3+ years of daily data) and careful tuning. It is expensive to train, harder to debug, and slower to serve. For stable commodities (wheat, rice, pulses), XGBoost on tabular lag features outperforms LSTM with far less complexity.
**Instead:** XGBoost baseline for all 314 commodities first. Promote to LSTM only for high-CV commodities (onion, tomato, potato) where sequence modeling adds measurable accuracy.

---

## Build Order (Dependencies Drive Phases)

Every downstream component depends on the one above it. Build in this order — skipping steps causes rework.

```
Phase 1: District Harmonisation
  ├── Script: harmonise_districts.py
  ├── DB table: district_name_map
  └── BLOCKS: every cross-dataset feature join (rainfall, weather, soil)

Phase 2: Seasonal Calendar (aggregation only, zero model risk)
  ├── Script: train_seasonal.py (reads parquet → writes seasonal_price_stats)
  ├── DB table: seasonal_price_stats
  ├── FastAPI: GET /api/v1/ml/seasonal
  └── BLOCKS: frontend seasonal calendar dashboard

Phase 3: Feature Engineering Foundation
  ├── ml/features/price_features.py (pure functions)
  ├── ml/features/rainfall_features.py
  ├── ml/features/soil_features.py
  └── BLOCKS: XGBoost and LSTM training scripts

Phase 4: XGBoost Price Forecasting
  ├── Script: train_xgboost.py (reads parquet, writes artifacts)
  ├── app/ml/loader.py (loads artifacts at startup)
  ├── DB table: forecast_cache
  ├── FastAPI: GET /api/v1/ml/forecast
  └── BLOCKS: frontend price chart with forecast overlay

Phase 5: Soil Crop Advisor
  ├── Script: seed_soil_suitability.py (one-time)
  ├── DB table: soil_crop_suitability
  └── FastAPI: GET /api/v1/ml/soil-advice

Phase 6: Arbitrage Dashboard
  ├── Derives from existing price_history data
  ├── FastAPI: GET /api/v1/ml/arbitrage
  └── Frontend: mandi differential table

Phase 7: LSTM for Volatile Commodities
  ├── Requires Phase 4 XGBoost baseline as quality benchmark
  ├── Script: train_lstm.py (onion, tomato, potato)
  ├── APScheduler: add refresh_forecasts_job
  └── Frontend: LSTM confidence band on price chart

Phase 8: Frontend Dashboards
  ├── Seasonal calendar (unblocks after Phase 2)
  ├── Forecast chart (unblocks after Phase 4)
  ├── Soil advisor UI (unblocks after Phase 5)
  └── Arbitrage map (unblocks after Phase 6)
```

**Why this order:**
- District harmonisation (Phase 1) is gating — without it, rainfall and soil features cannot join to price data.
- Seasonal calendar (Phase 2) is pure SQL aggregation: zero ML risk, immediate farmer value, validates that district harmonisation is working.
- Feature functions (Phase 3) must be built and tested before any model training — shared across XGBoost and LSTM.
- XGBoost baseline (Phase 4) must exist before LSTM — it provides the accuracy benchmark to beat and validates the serving infrastructure.
- Soil advisor (Phase 5) and Arbitrage (Phase 6) are independent of each other but both depend on Phase 1.

---

## Scalability Considerations

| Concern | Current Scale | At 10K users/day | At 1M users/day |
|---------|--------------|------------------|------------------|
| Forecast serving | PostgreSQL cache lookup, ~5ms | Add index on forecast_cache; pre-warm cache at 03:00 for top 100 (commodity, district) pairs | Redis cache layer in front of PostgreSQL; model serving process separate from API |
| Training data reads | Parquet (25M rows, on disk) | Same — parquet reads are offline | S3 or object storage for parquet; separate training cluster |
| Model memory | ~500 MB in-memory (top commodities) | Same | Per-commodity model servers; K8s per-replica model loading |
| DB write pressure | Low — forecast_cache writes are batch | Partition forecast_cache by generated_at month | Time-series DB (TimescaleDB) for price_history |
| Feature computation | DB query (180-day window, indexed) | Materialised view for recent price stats | Online feature store (Feast) |

---

## Sources

- FastAPI lifespan events: https://fastapi.tiangolo.com/advanced/events/ (MEDIUM confidence — verified against FastAPI official docs pattern used in `main.py`)
- APScheduler CronTrigger: https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html (HIGH confidence — existing codebase already uses APScheduler successfully)
- XGBoost agricultural forecasting effectiveness: https://pmc.ncbi.nlm.nih.gov/articles/PMC11431005/ (MEDIUM confidence — peer-reviewed 2025 paper)
- pandas parquet predicate pushdown: https://pandas.pydata.org/pandas-docs/stable/user_guide/scale.html (HIGH confidence — official pandas docs)
- pandas server-side cursor chunking: https://pythonspeed.com/articles/pandas-sql-chunking/ (MEDIUM confidence — verified against PostgreSQL docs)
- PostgreSQL UNLOGGED table as cache: https://martinheinz.dev/blog/105 (MEDIUM confidence — multiple sources agree)
- Model disk serialisation (joblib vs pickle): https://medium.com/nlplanet/is-it-better-to-save-models-using-joblib-or-pickle-776722b5a095 (MEDIUM confidence — verified against scikit-learn docs)
- PyTorch state_dict save/load: https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html (HIGH confidence — official PyTorch docs)
- Production ML deployment patterns: https://www.dataa.dev/2025/12/03/production-model-deployment-patterns-from-rest-apis-to-kubernetes-orchestration-in-python/ (MEDIUM confidence — recent article, consistent with observed FastAPI patterns)
- PostgreSQL vs Redis for caching: https://dizzy.zone/2025/09/24/Redis-is-fast-Ill-cache-in-Postgres/ (MEDIUM confidence — multiple benchmarks consistent)
