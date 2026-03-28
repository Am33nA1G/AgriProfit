# Technology Stack: AgriProfit ML Intelligence Layer

**Project:** AgriProfit — ML additions to existing FastAPI + PostgreSQL + Next.js platform
**Researched:** 2026-03-01
**Scope:** Python ML stack only — existing platform stack (FastAPI, SQLAlchemy, PostgreSQL, Next.js) is already shipped and not re-researched here.

---

## Recommended Stack

### 1. Tabular Price Forecasting (XGBoost baseline)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| xgboost | **3.2.0** (Feb 2026) | Gradient-boosted trees for 7–30 day price forecasting per commodity+district | Best-in-class tabular accuracy; handles missing features gracefully (rainfall/weather absent for ~55% of districts); native support for early stopping prevents overfitting on sparse commodity-district pairs |
| scikit-learn | **1.8.0** (Dec 2025) | Preprocessing, cross-validation, Pipeline scaffolding | TimeSeriesSplit for walk-forward validation; ensures no future leakage; required as XGBRegressor wrapper base |
| skforecast | **0.20.1** (Feb 2026) | Recursive multi-step forecasting wrapper around XGBRegressor | Handles the recursive prediction loop (day+1 forecast feeds day+2 input) correctly; 0.20.1 adds `inplace_predict` XGBoost path — 10x faster interval predictions; ForecasterRecursive wraps any sklearn-compatible estimator |

**Why XGBoost over LightGBM as primary:** XGBoost 3.x has cleaner external memory support for 25M-row batched training. Both are valid; XGBoost is the safer default for the baseline. LightGBM is used as the ensemble candidate once baseline passes (see below).

**Why NOT scikit-learn GradientBoostingRegressor:** 10-100x slower than XGBoost/LightGBM for same accuracy. No path to GPU acceleration.

**Why NOT Prophet:** Prophet is designed for single-series forecasting with implicit seasonality. We have 314 commodities × 571 districts = up to 179,294 series. Training 179K Prophet models is computationally prohibitive and Prophet cannot accept exogenous features cleanly (rainfall, soil, weather).

---

### 2. LightGBM (Ensemble Candidate and Volatile Commodity Baseline)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| lightgbm | **4.6.0** (Feb 2025) | Second gradient-boosted tree model; ensemble with XGBoost for Tomato/Onion/Potato | LightGBM trains faster on sparse commodity-district pairs (leaf-wise growth); often wins volatile series where XGBoost overfits; ensemble of the two consistently beats either alone in agricultural forecasting literature |

**Decision:** Train XGBoost first as baseline. Train LightGBM on the same feature set. Use simple average ensemble for commodities where CV > 20% (Tomato CV=34%, Onion CV=26%). Skip ensemble for stable commodities (Wheat CV=2%) where XGBoost alone is sufficient.

---

### 3. LSTM Sequence Models (Volatile Commodities: Onion, Tomato, Potato)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| torch | **2.10.0** (Jan 2026) | LSTM architecture for sequence modelling | PyTorch 2.x `torch.compile()` gives 2x speedup on CPU for LSTM inference vs PyTorch 1.x; standard for research-grade time series models; supports `model.eval()` + `torch.no_grad()` for inference-only serving |

**LSTM architecture decision:** Single-layer bidirectional LSTM (hidden_size=64–128, sequence_length=30 days) is sufficient for commodity price prediction. Transformer architectures (TFT, PatchTST) are more accurate on long sequences but require far more data per series — at 25M rows total but only ~1,000–5,000 rows per commodity-district pair after grouping, LSTM generalization is better. Use PyTorch `nn.LSTM` directly (not any framework abstraction) to keep the model small and serialisable with `torch.save`.

**Why NOT TensorFlow/Keras:** Project already has a Python/FastAPI environment. PyTorch is now the dominant framework for research and deployment (65%+ of ML papers, 2024). Mixing TF into a PyTorch-first repo adds dependency weight.

**Why NOT neuralforecast/NeuralProphet:** Both add heavy abstraction layers. For 3 volatile commodities, a direct `nn.LSTM` in 150 lines is simpler to debug and retrain than opaque framework internals.

---

### 4. Feature Engineering Pipeline

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pandas | **2.2.x** (already in project) | Lag feature creation, rolling stats, groupby temporal transforms | Already used in project; `.shift()` + `.rolling()` are the correct primitives for time-series feature engineering at 25M row scale with date filters |
| feature-engine | **1.9.4** (Feb 2026) | `LagFeatures`, `WindowFeatures`, `ExpandingWindowFeatures` as sklearn-Pipeline-compatible transformers | Saves 200+ lines of boilerplate; transformers implement `fit()`/`transform()` so they slot into sklearn `Pipeline`; critical for preventing train-test leakage (fit on train, transform on test) |
| statsmodels | **0.14.6** (Dec 2025) | `STL` seasonal decomposition to extract trend + residual components as features | `STL` is robust to outliers (unlike classical `seasonal_decompose`); trend and residual components from a 52-week decomposition are high-value features for XGBoost, particularly for Onion/Tomato where the seasonal component is strong but non-stationary |
| numpy | **1.26.x / 2.x** (already in project) | Numerical array operations within feature pipeline | Already present |

**sklearn Pipeline vs custom pipeline decision:**

Use **sklearn `Pipeline`** for the feature engineering + XGBoost training step. Rationale:
- `Pipeline.fit()` on training fold, `Pipeline.transform()` on test fold — eliminates an entire class of leakage bugs.
- Feature-engine transformers are Pipeline-compatible; XGBRegressor is Pipeline-compatible.
- `skforecast.ForecasterRecursive` accepts any sklearn-compatible Pipeline as its `regressor` argument — the entire feature-transform + model chain becomes one serialisable object.

Do **NOT** use a fully custom pipeline class. The sklearn Pipeline API is well-tested and covers all required operations. Custom code introduces bugs that are hard to detect (silent leakage through `.fit_transform()` called on the wrong split).

---

### 5. District Name Fuzzy Matching

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| rapidfuzz | **3.14.3** (Nov 2025) | Fuzzy string matching to harmonise 571 district names across 4 datasets | C++ implementation — 10-50x faster than `thefuzz` (Python); MIT licence (thefuzz uses GPL which conflicts with commercial products); `process.cdist()` computes full similarity matrix in a single vectorised call; `WRatio` scorer handles abbreviation + transliteration variants ("Nashik" / "Nasik" / "Nasik Dist") |

**Implementation pattern for the `district_name_map` table:**

```python
from rapidfuzz import process, fuzz

# Step 1: Build canonical list from Agmarknet (price data) — 571 districts
# Step 2: For each dataset (rainfall 616, soil 731, weather 290), match against canonical
# Step 3: Manual review for all matches below threshold 85
# Step 4: Write to district_name_map table with source, canonical, matched_name, score

matches = process.cdist(
    rainfall_districts,    # queries
    canonical_districts,   # choices
    scorer=fuzz.WRatio,
    workers=-1,            # use all CPU cores
)
```

`process.cdist` with `workers=-1` parallelises across all cores. For 616 × 571 = 351,936 comparisons, this completes in milliseconds. Store results in `district_name_map` with a `confidence` column; flag any score < 85 for manual review.

**Why NOT phonetic matching (Soundex/Metaphone):** Transliterations of Indian district names do not follow English phonetic rules consistently. "Murshidabad" and "Murshidabad" will match via Levenshtein but "Nashik" vs "Nasik" will not reliably match via Soundex. `fuzz.WRatio` (token sort + partial ratio) handles these cases better.

---

### 6. Model Serialisation and Serving

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| joblib | **1.4.x** (part of scikit-learn install) | Serialise sklearn `Pipeline` objects (feature-engine + XGBRegressor) | Joblib handles large NumPy arrays inside sklearn objects efficiently via memory-mapped files; `compress=3` gives good size/speed tradeoff; do NOT use pickle directly (less efficient, same security caveats) |
| torch.save / torch.load | built-in (PyTorch 2.10.0) | Serialise PyTorch LSTM `state_dict` | Standard PyTorch serialisation; `state_dict` (not full model pickle) is safer across PyTorch minor versions; load with `model.load_state_dict()` at FastAPI startup |

**Why NOT ONNX for this project:**

ONNX is correct for cross-language serving (Python → C++, mobile, edge). This project serves entirely within Python/FastAPI. ONNX adds a conversion step and `sklearn-onnx` / `onnxmltools` do **not** support all feature-engine transformers. The conversion would need to be re-validated every time a transformer is added or updated. Joblib + `model.state_dict()` is simpler, faster to iterate, and still production-adequate for a Python-only serving environment.

Revisit ONNX if inference latency becomes a bottleneck (>500ms per request) — XGBoost's native C++ `Booster.inplace_predict()` via skforecast already eliminates most Python overhead.

---

### 7. FastAPI Model Serving Pattern

**Pattern: lifespan-scoped singleton, loaded at startup**

```python
# backend/app/ml/model_registry.py
from contextlib import asynccontextmanager
import joblib
import torch

_registry: dict = {}

@asynccontextmanager
async def ml_lifespan(app):
    # Load all models once at startup; hold in memory
    _registry["xgb_pipeline"] = joblib.load("models/xgb_price_forecast.joblib")
    _registry["lstm_state"] = torch.load("models/lstm_volatile.pt", map_location="cpu")
    yield
    _registry.clear()

def get_model(key: str):
    return _registry[key]
```

**Why:** FastAPI's `lifespan` context manager (not deprecated `@app.on_event("startup")`) is the current recommended pattern. Loading at startup means zero cold-start latency on first request. The dict is never mutated after startup — satisfies the immutability principle.

**Caching forecast results:** Cache at the database layer (`forecast_cache` table) not in-process. Rationale: multiple Uvicorn workers do not share in-process state. A `forecast_cache` table with a `(commodity_id, district_id, forecast_date, horizon_days)` unique constraint serves all workers. Forecasts are deterministic given the same input data, so a 24-hour TTL is appropriate.

**Model versioning filename convention:**

```
models/xgb_price_forecast_v{MAJOR}_{YYYYMMDD}.joblib
models/lstm_volatile_v{MAJOR}_{YYYYMMDD}.pt
```

Symlink `xgb_price_forecast.joblib → xgb_price_forecast_v1_20260301.joblib` for zero-downtime model swaps. The `MAJOR` version increments only when the feature schema changes (new columns added/removed), requiring a full retrain of all downstream series.

---

### 8. Model Retraining Cadence

| Model | Cadence | Trigger | Rationale |
|-------|---------|---------|-----------|
| XGBoost tabular (all commodities) | Monthly | APScheduler cron job, 1st of month | Price data syncs daily but model accuracy degrades slowly; monthly is the sweet spot between resource cost and drift correction |
| LightGBM ensemble (volatile: Onion/Tomato/Potato) | Weekly | APScheduler cron job, Sunday 02:00 | High-volatility commodities drift faster; CV=34% for Tomato means weekly retraining catches seasonal regime changes |
| LSTM (Onion/Tomato/Potato) | Monthly | Same APScheduler job as XGBoost | LSTM training is more expensive (GPU/CPU time); monthly is adequate because LSTM captures structural patterns not ephemeral price spikes |
| Seasonal price calendar | On data sync | Triggered when new price data exceeds 30-day gap | Pure aggregation — cheap to recompute; staleness is immediately visible to users |

**Implementation:** Extend the existing `APScheduler BackgroundScheduler` in `app/integrations/scheduler.py`. Add retrain jobs as separate functions. Write retrained models to versioned filenames; update the symlink atomically. Log retrain metrics (RMSE, MAE per commodity) to a `model_training_log` table.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Tabular forecasting | XGBoost 3.2 + skforecast 0.20.1 | Prophet | Prophet cannot handle exogenous features cleanly; training 179K series is prohibitive |
| Tabular forecasting | XGBoost 3.2 | AutoML (AutoGluon, FLAML) | AutoML adds 2–5 GB of dependencies; overkill for a known, well-structured time series problem; makes retraining opaque |
| LSTM framework | PyTorch 2.10 nn.LSTM | TensorFlow/Keras | PyTorch is now dominant (2024–2026); avoids dual-framework dependency; lighter install |
| LSTM framework | PyTorch 2.10 nn.LSTM | neuralforecast / NeuralProphet | Abstraction overhead; difficult to debug; LSTM implementation in raw PyTorch is ~150 lines |
| Serialisation | joblib (sklearn) + torch.save (LSTM) | ONNX | ONNX conversion unsupported for feature-engine transformers; Python-only serving makes ONNX overhead unjustified |
| Fuzzy matching | RapidFuzz 3.14.3 | thefuzz (FuzzyWuzzy) | thefuzz is 10–50x slower; GPL licence; effectively deprecated in favour of RapidFuzz by the same authors |
| Fuzzy matching | RapidFuzz process.cdist | spaCy / sentence-transformers embeddings | Semantic embeddings are overkill for structured administrative names; Levenshtein/WRatio is the correct metric for typo/transliteration variants |
| Feature pipeline | sklearn Pipeline + feature-engine | Custom pandas transformer | Custom code introduces subtle leakage bugs; sklearn Pipeline fit-on-train/transform-on-test contract eliminates a class of errors |
| Feature pipeline | feature-engine 1.9.4 LagFeatures | tsfresh | tsfresh generates 700+ features automatically — computationally prohibitive at 25M row scale; most features irrelevant for 7–30 day agricultural price horizons |

---

## Installation

```bash
# ML core
pip install xgboost==3.2.0 lightgbm==4.6.0 scikit-learn==1.8.0 skforecast==0.20.1

# PyTorch CPU (no CUDA on production server assumed)
pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu

# Feature engineering
pip install feature-engine==1.9.4 statsmodels==0.14.6

# Fuzzy matching
pip install rapidfuzz==3.14.3

# Serialisation (joblib ships with scikit-learn; explicit pin for clarity)
pip install joblib==1.4.2
```

**Note on PyTorch CPU wheel:** The CPU-only wheel is ~250 MB vs ~2 GB for CUDA. Since training is offline (not in the serving container), use CPU wheel in production. Train on GPU locally or in a CI job, then copy serialised `state_dict` to the server.

---

## Critical Data Scale Constraints

These are not library choices but constraints that affect every library decision:

1. **25M rows — ALWAYS filter by date before feature engineering.** A rolling mean over the full table without a date filter causes a 60s+ timeout (learned from transport engine work). Feature engineering must query `WHERE price_date >= :start AND price_date <= :end` and operate on the filtered subset.

2. **Per commodity-district series have sparse data.** A niche commodity in a small district may have 200–800 rows total. Feature engineering with 30-day lags drops 30 rows per series. For short series (<180 rows after lag creation), skip LSTM and use XGBoost only — insufficient sequence length for LSTM convergence.

3. **Multi-series training with skforecast ForecasterRecursiveMultiSeries.** Train one model per commodity across all districts (not one model per commodity-district pair). This pools data across districts, dramatically improving generalisation for sparse district-commodity combinations. District identity becomes a categorical feature.

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| XGBoost version 3.2.0 (Feb 2026) | [pypi.org/project/xgboost](https://pypi.org/project/xgboost/) | HIGH |
| LightGBM version 4.6.0 (Feb 2025) | [pypi.org/project/lightgbm](https://pypi.org/project/lightgbm/) | HIGH |
| skforecast version 0.20.1 (Feb 2026), inplace_predict XGBoost path | [pypi.org/project/skforecast](https://pypi.org/project/skforecast/) + [skforecast.org/0.20.1/releases](https://skforecast.org/0.20.1/releases/releases) | HIGH |
| PyTorch version 2.10.0 (Jan 2026) | [pypi.org/project/torch](https://pypi.org/project/torch/) | HIGH |
| scikit-learn version 1.8.0 (Dec 2025) | [pypi.org/project/scikit-learn](https://pypi.org/project/scikit-learn/) | HIGH |
| statsmodels version 0.14.6 (Dec 2025) | [pypi.org/project/statsmodels](https://pypi.org/project/statsmodels/) | HIGH |
| RapidFuzz version 3.14.3 (Nov 2025), C++ backend, MIT licence | [pypi.org/project/RapidFuzz](https://pypi.org/project/RapidFuzz/) | HIGH |
| feature-engine version 1.9.4 (Feb 2026), LagFeatures + WindowFeatures | [pypi.org/project/feature-engine](https://pypi.org/project/feature-engine/) | HIGH |
| ONNX limitation: sklearn-onnx does not support all third-party estimators | [scikit-learn.org/stable/model_persistence.html](https://scikit-learn.org/stable/model_persistence.html) | HIGH |
| FastAPI lifespan is current recommended pattern over @app.on_event | [fastapi.tiangolo.com/advanced/events](https://fastapi.tiangolo.com/advanced/events/) | HIGH |
| LSTM vs XGBoost for volatile agricultural commodities | [ScienceDirect hybrid forecasting paper (2025)](https://www.sciencedirect.com/science/article/pii/S2214845025001553) | MEDIUM |
| XGBoost walk-forward validation (not k-fold) requirement | [skforecast.org forecasting with XGBoost](https://skforecast.org/0.13.0/user_guides/forecasting-xgboost-lightgbm) | HIGH |
| Weekly retraining for volatile series, monthly for stable | [mlinproduction.com/model-retraining](https://mlinproduction.com/model-retraining/) | MEDIUM |
| RapidFuzz process.cdist workers=-1 for parallelism | [rapidfuzz.github.io/RapidFuzz/Usage/process.html](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html) | HIGH |
