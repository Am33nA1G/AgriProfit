# Project Research Summary

**Project:** AgriProfit — ML Intelligence Layer
**Domain:** Agricultural price intelligence and crop advisory (Indian smallholder farmer context)
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH (stack HIGH, pitfalls HIGH empirically verified, features MEDIUM, architecture HIGH)

## Executive Summary

AgriProfit is adding a machine learning intelligence layer to an already-shipped FastAPI + PostgreSQL + Next.js platform with a working transport logistics engine and 25M rows of Agmarknet price history. The recommended approach is a data-engineering-first, ML-second sequence: harmonise district names across four heterogeneous datasets before any model touches a feature, build the seasonal price calendar as a pure-SQL first user-facing feature, then layer in XGBoost forecasting, soil crop advice, and mandi arbitrage in dependency order. LSTM models for volatile commodities (onion, tomato, potato) come last — after the XGBoost baseline is validated and serving — not alongside it. No new microservices or databases: all models are serialised to disk, loaded at FastAPI startup via the existing lifespan pattern, and forecasts are cached in a PostgreSQL table.

The highest-confidence finding across all four research streams is that data quality, not model sophistication, determines success. The raw Agmarknet parquet contains prices spanning nine orders of magnitude (including one value at 6.875 × 10^17 rupees/quintal), over 12,000 commodity-district pairs with 90-day data gaps, and district name spellings that diverge systematically across the four datasets. Addressing these before training is not optional cleanup — it is Phase 1. Every ML feature downstream depends on correct cross-dataset joins, winsorised price series, and a validated district harmonisation map.

The key risks are three: (1) silent data corruption from price unit errors and outliers that allows models to train without errors but produce nonsensical predictions, (2) look-ahead bias from rolling features computed before the train/test split, and (3) presenting block-average soil distributions as field-level soil facts — a failure mode that directly mirrors why the government's Soil Health Card scheme achieved only 49% farmer adoption. All three are preventable at build time with the patterns documented in PITFALLS.md. The stack choices (XGBoost via skforecast, sklearn Pipeline + feature-engine, RapidFuzz for district matching) were specifically selected to make these pitfalls structurally harder to trigger rather than just documented as warnings.

---

## Key Findings

### Recommended Stack

The ML stack slots into the existing Python/FastAPI environment with no new infrastructure dependencies. XGBoost 3.2.0 via skforecast 0.20.1 is the primary forecasting model — it handles missing features gracefully (critical because weather data covers only 46% of districts), supports the sklearn Pipeline API that enforces train/test isolation, and trains fast enough for 314-commodity-scale batch jobs. LightGBM 4.6.0 is the ensemble candidate specifically for high-CV commodities (Tomato CV=34%, Onion CV=26%) where ensemble consistently outperforms either model alone. PyTorch 2.10.0 (CPU wheel) is reserved for LSTM sequence modelling on those same three volatile commodities — architecture constraint is 1 layer, 64 hidden units, dropout 0.2 to prevent overfitting on the ~1,095 available training windows per commodity. All feature engineering uses sklearn Pipeline + feature-engine 1.9.4 transformers, which enforce fit-on-train/transform-on-test by construction and eliminate an entire class of leakage bugs that custom pandas code cannot prevent.

**Core technologies:**
- `xgboost==3.2.0` + `skforecast==0.20.1`: Recursive multi-step tabular forecasting — best-in-class for structured time series; `inplace_predict` gives 10x faster interval predictions; ForecasterRecursiveMultiSeries pools data across districts to handle sparse pairs
- `lightgbm==4.6.0`: Ensemble partner for CV>20% commodities — leaf-wise growth trains faster on sparse series where XGBoost overfits
- `torch==2.10.0` (CPU): Single-layer bidirectional LSTM for onion/tomato/potato only — `torch.compile()` gives 2x CPU inference speedup; `state_dict` serialisation is version-safe
- `scikit-learn==1.8.0`: TimeSeriesSplit for walk-forward validation; Pipeline API enforces leakage prevention
- `feature-engine==1.9.4`: LagFeatures, WindowFeatures as Pipeline-compatible transformers — saves 200+ lines of boilerplate; eliminates manual leakage risk
- `statsmodels==0.14.6`: STL decomposition for trend + residual features on seasonal commodities (robust to COVID/spike outliers, unlike classical seasonal_decompose)
- `rapidfuzz==3.14.3`: C++ fuzzy matching for district harmonisation — 10-50x faster than thefuzz; MIT licence; `process.cdist(workers=-1)` parallelises 600K+ comparisons in milliseconds
- `joblib==1.4.2`: sklearn Pipeline serialisation — handles large NumPy arrays via memory-mapped files; `compress=3` balances size/speed
- Model serving: FastAPI lifespan singleton pattern; forecast results cached in `forecast_cache` PostgreSQL table (24h TTL); no Redis

**Do NOT use:** Prophet (cannot handle exogenous features; prohibitive at 179K series scale), ONNX (feature-engine transformers unsupported; Python-only serving makes it unnecessary), tsfresh (700+ auto-features at 25M row scale is computationally prohibitive).

### Expected Features

Features are anchored to the Indian smallholder farmer context: low-to-medium digital literacy, district granularity, harvest/sale cycle decision-making, and chronic information asymmetry relative to traders.

**Must have (table stakes):**
- Current price trend direction (up/down vs last week) — farmers read direction, not absolute price; every competing app shows this
- Nearest mandi results by default — already in transport engine; must be surfaced prominently
- Seasonal best-month indicator — no Indian consumer platform provides this; pure aggregation; highest farmer-value-to-engineering-effort ratio
- Coverage transparency — soil data is block-level, price data ends Oct 2025; must display data cutoff and scope prominently
- Simple vocabulary, no technical jargon — ML confidence scores must be translated to farmer language

**Should have (competitive differentiators — none of these exist in any current Indian agricultural app):**
- 7-day directional price forecast with confidence colour (Green/Yellow/Red) — first-mover gap; present as range not point
- "Sell now vs wait" signal — binary hold/sell derived from forecast direction + confidence; directly addresses farmers' core question
- Seasonal sell window calendar with 10-year data — bar chart with IQR bands; call out best 2-month window, not just single best month
- Crop recommendation from block soil deficit profile — NPK/pH distribution ranked against 3–5 suitable crops; market demand overlay from seasonal calendar
- Mandi arbitrage ranked by net profit after transport — reuses existing logistics engine; filter to NET margin > 10% threshold; top 3 mandis only
- Price confidence score — derived from CV%, data staleness, thin-market flags already in transport risk engine

**Defer to v2+:**
- LSTM price forecasting (build XGBoost baseline first; only promote to LSTM where it beats XGBoost by >5% RMSE)
- Weather-enhanced model for 260 covered districts (tiered improvement, not v1 blocker)
- Chatbot / conversational advisor (NLP pipeline complexity-to-value ratio is unfavorable for v1; DeHaat/BharatAgri failures confirm this)
- Yield prediction, MSP modeling, futures integration (explicitly out of scope; no data to support)
- Real-time price streaming (agmarknet data arrives with 1-2 day lag; "real-time" label would mislead farmers)

**Anti-features (explicitly do not build):**
- Precise rupee forecasts displayed as fact — MAPE 10-17% for volatile crops means ±₹200-340 error on ₹2000/q; destroys trust when wrong
- 30-day ML horizon for volatile crops — accuracy degrades sharply beyond 7-14 days for high-CV commodities; use historical seasonal pattern instead
- Individual field-level crop advice — soil data is block distribution, not field measurement; same mistake that caused 59% SHC non-adoption

### Architecture Approach

The ML layer adds two new directory trees to the existing backend: `backend/ml/` for offline training code (no FastAPI imports; reads parquet files, writes serialised artifacts) and `backend/app/ml/` for online serving code (FastAPI routes, service, loader — mirrors the existing `app/transport/` pattern). Four new SQLAlchemy models add PostgreSQL tables: `district_name_map`, `seasonal_price_stats`, `forecast_cache`, `soil_crop_suitability`. The existing APScheduler in `app/integrations/scheduler.py` is extended with a `refresh_forecasts_job()` that runs daily at 03:00 (2 hours after the existing price sync). No Redis, no separate model server, no object storage — disk files loaded at startup into `app.state.models` via the existing FastAPI lifespan event.

**Major components:**
1. `backend/ml/features/` — Pure Python feature functions (no I/O); same code path for training and serving; `price_features.py`, `rainfall_features.py`, `soil_features.py`, `weather_features.py`
2. `backend/ml/training/` — Offline scripts: `train_seasonal.py` (aggregation to DB), `train_xgboost.py` (reads parquet, writes joblib), `train_lstm.py` (PyTorch state_dict), `evaluate_models.py` (walk-forward RMSE logging)
3. `backend/ml/artifacts/` — Versioned serialised models on disk; git-ignored; filename convention `{commodity}_{state}_v{N}.joblib`; symlink for zero-downtime swaps
4. `backend/app/ml/loader.py` — Loads all artifacts at FastAPI startup into `app.state.models` dict; LRU eviction when total exceeds memory limit
5. `backend/app/ml/routes.py` + `service.py` — Forecast endpoint checks `forecast_cache` first (5ms cache hit); on miss, assembles features from DB (last 180d, date-filtered), runs inference, upserts cache
6. `app/models/forecast_cache.py` — PostgreSQL cache with `(commodity_id, district_id, horizon_days, forecast_date)` unique constraint; `model_version` column for invalidation on retrain
7. `app/models/soil_crop_suitability.py` — Precomputed lookup table from offline rule-based script; no ML model; updated when new soil survey data arrives
8. Next.js dashboards — `/ml/seasonal`, `/ml/forecast`, `/ml/soil`, `/ml/arbitrage` — read from `/api/v1/ml/*`; no direct DB access

**Key architecture decisions:**
- Train from parquet (not live DB) — zero read pressure on production during training; predicate pushdown makes 25M-row reads practical
- Soil advice is a rule-based lookup, not a live ML model — NPK/pH thresholds are deterministic; precomputed suitability scores are simpler, more interpretable, and correct
- Two-tier weather model — districts with weather data use full feature set (Tier A, ~260 districts); remaining use rainfall-only (Tier B, ~300 districts); never impute missing weather with global means

### Critical Pitfalls

1. **Price unit corruption corrupting all models** — Raw Agmarknet contains values spanning nine orders of magnitude (including 6.875×10^17). Winsorise per commodity at `median × 20` BEFORE any feature engineering. Store winsorisation bounds in a `price_bounds` table so the same bounds apply at inference. Never use global winsorisation — commodity price ranges differ 100x. [Phase 1]

2. **Look-ahead bias via rolling features computed before split** — Rainfall for month M must be lagged by 1 full month (not used same-month). Rolling statistics must be computed within each walk-forward fold, never on the full dataset before splitting. Use sklearn Pipeline with `cutoff_date` parameter enforced in all feature functions — the Pipeline contract makes this structural, not advisory. [Phase 3]

3. **Random train/test split on time series** — `sklearn.train_test_split` silently destroys temporal ordering. Use `TimeSeriesSplit` with 4 walk-forward folds (train 2015-N, validate N+1; N = 2020..2023). A 30-day gap between last training row and first validation row is mandatory to prevent rolling feature bleed-through. If validation RMSE is better than training RMSE, leakage is present. [Phase 4]

4. **District harmonisation cascade errors** — 19% of price↔soil districts (107 districts) need fuzzy matching. Generic global fuzzy match achieves only 47.5% accuracy on Hindi district names; state-scoped matching achieves 93.1%. Always scope RapidFuzz matching within state boundaries. Use three-tier confidence: exact-match accept, fuzzy-match accept (score > 0.90), manual review (0.75-0.90), flag unmatched. Store `match_type` column. [Phase 1]

5. **Soil distributions presented as field-level precision** — The soil parquet schema is `(high_pct, medium_pct, low_pct)` — a statistical distribution across sampled fields in a block, not a measurement of any specific field. Never convert to a single label. Display the full distribution in the UI: "92% of fields in this block have medium nitrogen. Your field may differ." Include block sample size as confidence indicator. This is the same mistake that caused 59% SHC non-adoption. [Phase 5]

---

## Implications for Roadmap

Research across all four streams converges on the same dependency order. This is not a stylistic choice — it is dictated by data dependencies that cannot be reordered.

### Phase 1: Data Foundation — District Harmonisation and Price Cleaning

**Rationale:** All four ML features (seasonal calendar, price forecasting, crop recommendation, arbitrage) require correct cross-dataset joins. The 19% of price-soil districts unmatched by exact string matching, the CV% outliers from price unit corruption, and the policy discontinuity periods (demonetisation 2016, COVID 2020, onion export bans) must all be addressed before any model sees data. Building anything else first produces wrong results that are expensive to retrofit.

**Delivers:**
- `district_name_map` table with state-scoped fuzzy matching and manual review for gray-zone matches
- `price_bounds` table with per-commodity winsorisation bounds
- `policy_events` table (10-15 key events: demonetisation, COVID lockdown, onion export bans)
- `harmonise_districts.py` script with three-tier confidence (exact / fuzzy-accepted / manual)

**Addresses:** Table-stakes coverage transparency (data quality signals visible to users)
**Avoids:** Cascade errors from global fuzzy matching (Pitfall 5); price corruption baked into all models (Pitfall 1)
**Research flag:** Standard data engineering patterns — no deeper research needed. Validate by spot-checking 20 manually selected district matches before proceeding.

---

### Phase 2: Seasonal Price Calendar

**Rationale:** Highest farmer value per engineering hour. Pure SQL aggregation on already-available price data — no ML model risk, no training infrastructure, no model validation. Validates that district harmonisation is working correctly (seasonal patterns should match known agricultural calendars: onion peaks Oct-Nov, tomato peaks Jul in West Bengal / Feb-Mar in Karnataka). First user-facing feature shipped.

**Delivers:**
- `train_seasonal.py` — aggregates 10-year parquet to monthly median/IQR per commodity+state+district
- `seasonal_price_stats` DB table
- `GET /api/v1/ml/seasonal` endpoint
- Next.js seasonal calendar dashboard with best-2-month highlight
- Validation: spot-check against known seasonal patterns before release

**Addresses:** Seasonal best-month indicator (table stakes), seasonal sell window calendar (differentiator)
**Uses:** pandas, statsmodels STL for decomposition, existing PostgreSQL
**Avoids:** COVID-era data distorting 10-year averages (Pitfall 11) — use median not mean; compute pre/post-2020 separately; require 30+ observations per month
**Research flag:** No additional research needed. Standard aggregation patterns.

---

### Phase 3: Feature Engineering Foundation

**Rationale:** Feature functions are shared across XGBoost training and LSTM training. Building and unit-testing them as pure functions before any model training prevents the most expensive class of bugs — look-ahead bias that produces optimistic training metrics but fails in production. This phase has no user-facing output but gates everything downstream.

**Delivers:**
- `ml/features/price_features.py` — lag features (7, 14, 30, 60d), rolling mean/std, month-of-year dummies, all accepting `cutoff_date` parameter
- `ml/features/rainfall_features.py` — monthly deficit/surplus lagged 1 month; completeness check per district per year (require 10/12 months)
- `ml/features/soil_features.py` — NPK/pH deficiency scores per block from distribution data
- `ml/features/weather_features.py` — Tier A features for 260 covered districts only; no imputation
- Daily time series grid reindexing (create complete date range, NaN for missing mandi days, `days_since_last_observation` as explicit feature)
- Unit tests for all feature functions (leakage detection test: train years 1-7, manually inspect test-period feature values)

**Avoids:** Look-ahead bias (Pitfall 2); missing mandi days treated as adjacent days (Pitfall 9); weather coverage gap silently degrading model quality for 54% of districts (Pitfall 10)
**Research flag:** No additional research needed. Patterns are well-established in sklearn Pipeline documentation.

---

### Phase 4: XGBoost Price Forecasting Baseline

**Rationale:** The baseline model must exist and be validated before LSTM is attempted. It also validates the serving infrastructure (model registry, forecast cache, loader) that LSTM will reuse. XGBoost trains faster, is easier to debug, and for stable commodities (Wheat CV=2%, Paddy, Turmeric) it will be the permanent production model — LSTM adds nothing for these.

**Delivers:**
- `train_xgboost.py` — ForecasterRecursiveMultiSeries per commodity group (pools districts); 730-day minimum threshold; sparse pairs routed to seasonal fallback
- Walk-forward evaluation: 4 folds (train 2015-N, validate N+1); RMSE logged to `model_training_log`
- `ml/artifacts/xgboost/` — versioned joblib files; symlink for zero-downtime swaps
- `app/ml/loader.py` — LRU model registry with memory limit; lazy loading per commodity-district
- `forecast_cache` DB table with `model_version` column
- `GET /api/v1/ml/forecast` endpoint with cache-first logic (5ms hit, full inference on miss)
- `app/ml/schemas.py` — ForecastResponse with range (not point), confidence colour, direction signal
- APScheduler extension: `refresh_forecasts_job()` at 03:00 daily
- Next.js price chart with 7-day forecast overlay and confidence band

**Addresses:** 7-day directional forecast (differentiator), "sell now vs wait" signal (differentiator)
**Avoids:** Random train/test split (Pitfall 3); training on sparse pairs (Pitfall 7); full-table DB scan during serving (all queries include `price_date >= NOW() - INTERVAL '180 days'`); training inside FastAPI endpoint (Pitfall from ARCHITECTURE.md)
**Research flag:** Walk-forward validation implementation is well-documented. Model hyperparameter tuning may need a short research spike — skforecast documentation covers this with concrete examples.

---

### Phase 5: Soil Crop Advisor

**Rationale:** Depends on Phase 1 (district harmonisation joins price data to soil blocks) and Phase 2 (seasonal calendar provides the market demand signal that ranks crops). Independent of XGBoost forecasting — can be built in parallel with Phase 4 if bandwidth allows, but depends on Phase 3 feature functions for soil features. Highest implementation complexity of all features due to the block-distribution data schema.

**Delivers:**
- `seed_soil_suitability.py` — rule-based scoring; NPK/pH thresholds per crop from agronomic literature; writes `soil_crop_suitability` table
- `GET /api/v1/ml/soil-advice` endpoint — lookup by district+block+season; returns top 3-5 ranked crops
- Response schema: crop name, soil suitability (YES/PARTIAL/NO with distribution), market demand (HIGH/MEDIUM/LOW from seasonal calendar), fertiliser deficit flag
- Next.js crop advisor UI showing full percentage distributions (not single labels), explicit block-average disclaimer, KVK referral for soil testing

**Addresses:** Crop recommendation from soil deficit profile (differentiator)
**Avoids:** Block-average soil presented as field-level precision (Pitfall 6) — UI schema shows distributions from day one; single-label display is a build-time constraint, not a post-launch retrofit
**Research flag:** NPK/pH threshold values per crop need validation against ICAR agronomic guidelines. This is a targeted research task (1-2 hours), not a full research-phase sprint.

---

### Phase 6: Mandi Arbitrage Dashboard

**Rationale:** Highest leverage relative to complexity — the transport logistics engine already computes net profit after freight, spoilage, and time. Arbitrage is a filter + sort on top of existing infrastructure. Depends on district harmonisation (Phase 1) for routing. Independent of ML forecasting phases.

**Delivers:**
- `GET /api/v1/ml/arbitrage` endpoint — queries price_history (last 7 days, date-filtered), computes cross-mandi spread, calls existing transport engine for net profit per route
- Filter: only mandis where NET margin > 10% of commodity price after transport
- Response: top 3 mandis ranked by net profit; distance, travel time, net gain/quintal, verdict badge
- Data freshness gate: suppress differentials if either mandi has no data within 7 days; show `last_updated` prominently
- Next.js arbitrage dashboard

**Addresses:** Mandi arbitrage ranked by net profit after transport (differentiator); no Indian platform currently does this
**Avoids:** Stale price differentials misleading farmers on transport decisions (Pitfall 15); raw price differential display without transport cost (anti-feature)
**Research flag:** No additional research needed. Builds directly on existing transport engine patterns.

---

### Phase 7: LSTM for Volatile Commodities

**Rationale:** XGBoost baseline (Phase 4) must be in production before LSTM is started. LSTM is only deployed for commodity-district pairs where it beats XGBoost by > 5% RMSE on walk-forward validation. For onion, tomato, and potato with sufficient data (> 1095 days), the ensemble of XGBoost + LightGBM + LSTM consistently outperforms any single model. This phase also adds LightGBM ensemble and scheduled model retraining.

**Delivers:**
- `train_lstm.py` — single-layer bidirectional LSTM (hidden=64, dropout=0.2); sequence-to-one training; early stopping on walk-forward validation loss; compare to XGBoost baseline on same folds
- `ml/artifacts/lstm/` — versioned `.pt` state_dict files per volatile commodity
- LightGBM ensemble: train on same feature set as XGBoost; simple average ensemble for CV > 20% pairs
- Extended APScheduler: weekly LightGBM retrain (Sunday 02:00); monthly XGBoost + LSTM retrain (1st of month); log RMSE/MAE to `model_training_log`
- Updated forecast endpoint to select XGBoost vs ensemble based on commodity and data availability
- Frontend: LSTM confidence band on price chart for volatile commodities

**Addresses:** LSTM price forecasting (deferred from v1 baseline); weather-enhanced model (Tier A districts upgraded in this phase)
**Avoids:** LSTM for all commodities (Pitfall from ARCHITECTURE.md — keep stable commodities on XGBoost); LSTM overfitting on short sequences (Pitfall 12 — architecture constraint enforced in training script); stale forecasts after retrain (Pitfall 13 — `model_version` in cache key)
**Research flag:** Memory management for multi-worker FastAPI with large model sets needs explicit testing (Pitfall 8). Gunicorn `--preload` + copy-on-write behaviour with PyTorch LSTM must be validated — this is a known risk area per FastAPI GitHub discussion #7069.

---

### Phase Ordering Rationale

- **District harmonisation gates everything**: No cross-dataset feature join is valid without it. Building seasonal calendar or XGBoost features first and retroactively fixing join errors is a full rewrite, not a patch.
- **Seasonal calendar as proof-of-concept**: Validates harmonisation, delivers immediate farmer value, and produces zero model risk. If it fails (seasonal patterns don't match expectations), the failure is in data quality, not model choice — much easier to debug.
- **Feature functions before training scripts**: Shared code path between training and serving; leakage bugs caught at unit-test time cost hours; leakage bugs caught in production cost weeks.
- **XGBoost before LSTM**: LSTM needs a quality benchmark to beat. Without the XGBoost baseline, there is no principled way to decide whether LSTM is worth the complexity cost.
- **Soil and arbitrage are independent of each other**: They can be built in parallel after Phases 1-3 are complete if team bandwidth allows. The suggested order (soil Phase 5, arbitrage Phase 6) reflects complexity, not hard dependency.

### Research Flags

Phases needing deeper research during planning:
- **Phase 4 (XGBoost baseline):** Hyperparameter tuning strategy for ForecasterRecursiveMultiSeries at 314-commodity scale — skforecast docs have examples but optimal grid search bounds for agricultural data may need a targeted spike
- **Phase 7 (LSTM/ensemble):** Gunicorn multi-worker memory behaviour with PyTorch LSTM models — test `--preload` + copy-on-write explicitly before deploying; FastAPI GitHub discussion #7069 confirms this is a real risk

Phases with standard, well-documented patterns (no additional research needed):
- **Phase 1 (district harmonisation):** RapidFuzz `process.cdist` with state-scoped matching is well-documented; implementation is mechanical after the approach is decided
- **Phase 2 (seasonal calendar):** Pure SQL aggregation with pandas; median/IQR computation is standard
- **Phase 3 (feature engineering):** sklearn Pipeline + feature-engine patterns are fully documented; implementation is testing-intensive, not research-intensive
- **Phase 6 (arbitrage):** Direct extension of existing transport engine; no new technology

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI (Feb-Mar 2026). Technology choices validated against academic literature and official documentation. Version pins are recent and specific. |
| Features | MEDIUM | Competitor platform features directly observed (eNAM, agmarknet, Kisan Suvidha, AgriMarket). Forecast accuracy benchmarks from peer-reviewed 2024-2025 literature. Arbitrage threshold (10% net margin) is inferred, not sourced — LOW confidence on that specific number. |
| Architecture | HIGH | Grounded in existing codebase patterns (transport engine, APScheduler, lifespan startup). No new infrastructure invented. Build order validated against data dependency graph. |
| Pitfalls | HIGH | Pitfalls 1, 5, 6, 7, 9 are empirically verified against the actual parquet files in this project (CV% outliers, gap counts, soil schema). Pitfalls 2, 3 are from authoritative sources (Hyndman FPP3 textbook, peer-reviewed leakage papers). Pitfall 8 from official FastAPI GitHub discussion. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Arbitrage net-margin threshold (10%):** Inferred from transport cost analysis. Validate with a break-even calculation using actual freight costs from the transport engine before hardcoding. Consider making this a configurable parameter rather than a constant.
- **NPK/pH crop suitability thresholds:** Need to source from ICAR agronomic guidelines for the specific crop list. Do not rely on generic international thresholds — Indian agronomic conditions differ. A 1-2 hour targeted research task during Phase 5 planning.
- **LSTM memory behaviour under Gunicorn multi-worker:** The copy-on-write guarantee is confirmed in principle but PyTorch model forking has known edge cases. Must run an explicit test before Phase 7 deployment, not treat it as a known-safe assumption.
- **Model coverage for Phase 4 initial release:** With a 730-day minimum training threshold, determine how many of the 19,679 commodity-district pairs qualify before committing to a launch date. If fewer than expected qualify, the fallback to seasonal calendar for sparse pairs must be fully implemented and tested before Phase 4 ships.
- **Price data gap from Oct 2025 to present (2026-03-01):** Forecasts are retrospective validation + near-term projection, not live. The data freshness gap (4+ months) must be communicated in the UI and considered in holdout validation design — the most recent 4 months of parquet data are unavailable in the live DB.

---

## Sources

### Primary (HIGH confidence)
- PyPI package pages (xgboost, lightgbm, skforecast, torch, scikit-learn, statsmodels, rapidfuzz, feature-engine) — version verification
- FastAPI official docs — lifespan events pattern
- PyTorch official docs — state_dict save/load
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3rd ed.) — walk-forward validation
- FastAPI GitHub discussion #7069 — multi-worker RAM multiplication
- Government SHC Manual (NITI for States) — soil health card data schema

### Secondary (MEDIUM confidence)
- PMC/PubMed 2024-2025 agricultural price forecasting papers (Indian commodities; MAPE benchmarks)
- Nature Scientific Reports 2024 — exogenous-variable LSTM for TOP crops (onion/tomato/potato)
- Oxford Academic ERAE — COVID-19 effects on food prices in India
- ScienceDirect 2024 — marketing channel price differentials (13-73% mandi premium)
- IDInsight study — Hindi district name fuzzy matching accuracy (47.5% vs 93.1%)
- GSMA field research + Ama Krushi study — farmer digital literacy and UX patterns
- Skforecast 0.20.1 documentation — ForecasterRecursiveMultiSeries, inplace_predict

### Tertiary (LOW confidence — needs validation)
- Arbitrage threshold (10% net margin) — inferred from transport cost analysis, no primary source
- Weekly vs monthly retrain cadence recommendation — from mlinproduction.com, consistent with intuition but not peer-reviewed
- Memory threshold estimates for XGBoost model sizes (5-50 MB per model) — estimated from model complexity, not measured

---

*Research completed: 2026-03-01*
*Synthesized from: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md, PROJECT.md*
*Ready for roadmap: yes*
