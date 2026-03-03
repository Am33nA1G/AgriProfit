# Roadmap: AgriProfit ML Intelligence Platform

## Overview

This milestone adds a machine learning intelligence layer to the existing AgriProfit platform. Work proceeds in strict dependency order: district harmonisation unlocks every cross-dataset join, the seasonal calendar validates harmonisation with zero model risk, feature engineering builds the shared code path for all models, XGBoost forecasting establishes the serving baseline, and then the soil advisor and mandi arbitrage dashboard deliver the remaining farmer-facing features. LSTM forecasting is v2 — it builds on the XGBoost baseline that must be validated first.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: District Harmonisation + Price Cleaning** - Build the cross-dataset join foundation that gates all ML features
 (completed 2026-03-02)
- [ ] **Phase 2: Seasonal Price Calendar** - Deliver the first farmer-facing feature via pure SQL aggregation
- [x] **Phase 3: Feature Engineering Foundation** - Build and unit-test all shared feature functions before any model training
- [ ] **Phase 4: XGBoost Forecasting + Serving** - Train, validate, cache, and serve the price forecasting baseline
- [x] **Phase 5: Soil Crop Advisor** - Map block soil profiles to crop recommendations using ICAR rule-based lookup (completed 2026-03-03)
- [ ] **Phase 6: Mandi Arbitrage Dashboard** - Surface net-profit-ranked arbitrage signals using the existing transport engine

## Phase Details

### Phase 1: District Harmonisation + Price Cleaning
**Goal**: Every dataset can be joined by district with verified coverage, and every price series is free of unit-corruption outliers before any feature or model computation touches the data.
**Depends on**: Nothing (first phase)
**Requirements**: HARM-01, HARM-02, HARM-03, HARM-04
**Success Criteria** (what must be TRUE):
  1. The `district_name_map` table exists and maps all district name variants across prices, rainfall, weather, and soil datasets using state-scoped RapidFuzz matching — global fuzzy matching is not used anywhere
  2. Price-to-rainfall district join achieves >= 95% coverage (>= 543 of 571 price districts matched), verifiable by running the join and counting matched rows
  3. Price-to-soil district join covers all 21 states with soil data available in the local dataset (data/soil-health/nutrients/), verifiable by querying matched block records per state; harmonise_districts.py matched 20 of 21 available states at 95.2%
  4. Every price series has winsorisation bounds stored in a `price_bounds` table; outlier rows with CV > 500% are flagged and capped, not silently included in downstream computation
  5. A spot-check of 20 manually selected district matches (covering Hindi/English name variants) confirms correct state-scoped assignment before Phase 2 begins
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — District harmonisation (RapidFuzz state-scoped matching, district_name_map table, Alembic migration, ml module scaffold)
- [x] 01-02-PLAN.md — Price cleaning pipeline (per-commodity IQR winsorisation, price_bounds table, outlier flagging)
- [x] 01-03-PLAN.md — Gap closure: correct HARM-04 soil state count from 31 to 21 in REQUIREMENTS.md and ROADMAP.md

### Phase 2: Seasonal Price Calendar
**Goal**: A farmer can select any commodity and state and see a monthly sell-window chart built from 10 years of price history, with best and worst months clearly labelled.
**Depends on**: Phase 1
**Requirements**: SEAS-01, SEAS-02, SEAS-03, SEAS-04, UI-01, UI-05
**Success Criteria** (what must be TRUE):
  1. User can open the seasonal calendar page, select any of the 314 commodities and any state, and see a monthly price chart (median +/- IQR) without triggering a full-table scan on the 25M row price table
  2. The chart labels the best two months to sell and the worst month to avoid, derived from the 10-year aggregate — not from ad-hoc computation at request time
  3. Commodities or states with fewer than 3 years of monthly data display a visible low-confidence warning in the UI, not a chart that looks identical to high-confidence data
  4. The `seasonal_price_stats` table is populated by a training script that reads from the price parquet, not from live DB queries, and the endpoint reads only from that pre-aggregated table
  5. Known seasonal patterns are spot-checked before release: onion peaks Oct-Nov, tomato peaks Jul in West Bengal or Feb-Mar in Karnataka — a mismatch signals a data quality problem, not a model problem
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Alembic migration for seasonal_price_stats, pure aggregator module (TDD), train_seasonal.py offline pipeline
- [ ] 02-02-PLAN.md — FastAPI seasonal endpoint + Pydantic schemas + Next.js calendar dashboard with Recharts IQR chart

### Phase 3: Feature Engineering Foundation
**Goal**: All shared feature functions (price lags, rolling stats, rainfall deficit, weather, soil) exist as pure Python with unit tests and enforced cutoff_date parameters, with no look-ahead leakage possible.
**Depends on**: Phase 1
**Requirements**: FEAT-01, FEAT-02, FEAT-03, FEAT-04
**Success Criteria** (what must be TRUE):
  1. Lag features (7d, 14d, 30d, 90d) and rolling statistics (7d/30d mean, std) can be computed for any commodity-district series with a `cutoff_date` parameter that structurally prevents look-ahead — a leakage detection test (train on years 1-7, assert test-period feature values are not visible in training data) passes in CI
  2. Monthly rainfall deficit/surplus is available as a feature for all 543 harmonised price-rainfall district pairs (Tier A), with a completeness check that requires >= 10 of 12 months per district per year
  3. Daily temperature and humidity features are available for the ~261 weather-covered districts (Tier A+) and absent — not imputed — for the remaining ~310 districts (Tier B)
  4. All feature functions are pure Python with no database calls inside the function body — they accept DataFrames as input and return DataFrames as output, making them testable without a running database
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Price and rainfall feature functions (price_features.py, rainfall_features.py, cutoff_date enforcement, leakage detection test, unit tests)
- [x] 03-02-PLAN.md — Weather and soil feature functions (weather_features.py, soil_features.py, Tier A+/B split, unit tests)

### Phase 4: XGBoost Forecasting + Serving
**Goal**: A farmer can request a 7-day or 14-day price forecast for any commodity-district pair, receive a direction signal and predicted range (not a point estimate), and the system serves this from a PostgreSQL cache refreshed nightly — with walk-forward validation RMSE logged before any model enters production.
**Depends on**: Phase 3 (feature functions), Phase 1 (harmonised districts)
**Requirements**: FORE-01, FORE-02, FORE-03, FORE-04, FORE-05, FORE-06, SERV-01, SERV-02, SERV-03, SERV-04, UI-02, UI-05
**Success Criteria** (what must be TRUE):
  1. One XGBoost model exists per commodity group using ForecasterRecursiveMultiSeries, trained only on commodity-district pairs with >= 730 days of data; pairs below this threshold are routed to the seasonal calendar fallback, not served an ML forecast
  2. Every model's 4-fold walk-forward RMSE and MAPE are logged to a `model_training_log` table before the model file is written to `ml/artifacts/` — no model reaches serving without a logged validation record
  3. The `/api/v1/forecast/{commodity}/{district}` endpoint returns a response that includes direction (up/down/flat), predicted range (low/mid/high), a confidence colour (Green/Yellow/Red), and a tier label ("full model" or "seasonal average fallback")
  4. Forecast responses are served from the `forecast_cache` table on cache hit (target: <= 50ms); the APScheduler nightly job at 03:00 regenerates stale forecasts and incorporates new price data since the last refresh
  5. Model files are loaded into `app.state.models` via LRU cache at FastAPI startup — no model is loaded at startup for every commodity; models are lazy-loaded on first request and evicted when memory limit is exceeded
**Plans**: 5 plans

Plans:
- [ ] 04-01-PLAN.md — DB schema + ML dependencies (model_training_log migration, forecast_cache migration, SQLAlchemy ORM models, requirements.txt)
- [ ] 04-02-PLAN.md — XGBoost training script TDD (train_xgboost.py, walk-forward validation gate, test_ml_training.py)
- [ ] 04-03-PLAN.md — ML serving core (loader.py LRU cache, ForecastService, ForecastResponse schema, test_ml_loader.py, test_forecast_service.py)
- [ ] 04-04-PLAN.md — FastAPI wiring + scheduler (forecast/routes.py, main.py router + app.state, scheduler nightly job, test_forecast_api.py, test_scheduler.py)
- [ ] 04-05-PLAN.md — Next.js forecast UI (forecast page, ForecastChart component, direction/confidence badges, fallback banner)

### Phase 5: Soil Crop Advisor
**Goal**: A farmer can select a state, district, and block and receive a ranked list of suitable crops based on the block's NPK/pH soil deficiency profile, with fertiliser advice per nutrient deficit and an explicit disclaimer that the data is a block-level distribution, not a field-level measurement.
**Depends on**: Phase 1 (district-to-block harmonisation), Phase 4 (complete — seasonal demand signal available for crop ranking)
**Requirements**: SOIL-01, SOIL-02, SOIL-03, SOIL-04, SOIL-05, UI-03, UI-05
**Success Criteria** (what must be TRUE):
  1. User can drill down from state to district to block and see the NPK/pH percentage distributions (high/medium/low %) for the most recent soil health cycle — not a single label, the full distribution
  2. The block's deficiency profile maps to a ranked list of 3-5 suitable crops using ICAR NPK/pH threshold rules, with market demand (HIGH/MEDIUM/LOW from seasonal calendar) shown alongside each crop
  3. Every recommendation screen displays "Block-average soil data for [block name] — not a field-level measurement" as a non-dismissable disclaimer
  4. Fertiliser advice is generated per nutrient deficiency: for any nutrient where the low% distribution exceeds a threshold, the UI shows an explicit advice card (e.g. "73% of soils in this block are nitrogen-deficient — consider urea application before planting")
  5. The soil advisor page is labelled "Available for 21 states" and states with no soil coverage are clearly marked as unavailable — a user selecting an uncovered region sees an informative message, not an empty result or an error
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md — Alembic migration (soil_profiles + soil_crop_suitability tables), suitability.py + fertiliser.py pure functions (TDD), seed_soil_suitability.py bulk seeder
- [x] 05-02-PLAN.md — FastAPI soil advisor endpoints (states/districts/blocks/profile) + Next.js drill-down UI with disclaimer, distribution bars, crop list, fertiliser advice cards

### Phase 6: Mandi Arbitrage Dashboard
**Goal**: A farmer can select a commodity and their origin district and see the top 3 destination mandis ranked by net profit after freight and spoilage — using only price data fresher than 7 days, with stale data flagged rather than displayed as current.
**Depends on**: Phase 1 (harmonised districts for routing), Phase 4 (complete — confirms transport engine integration pattern)
**Requirements**: ARB-01, ARB-02, ARB-03, ARB-04, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. User can select a commodity and origin district and see the top 3 destination mandis ranked by net expected profit per quintal after freight cost, spoilage estimate, and loading/unloading costs are subtracted
  2. Arbitrage results are suppressed when net margin after transport does not exceed the configurable threshold (default: 10% of commodity modal price) — no result is shown rather than a misleading negative-margin result
  3. The dashboard only displays price differentials where both origin and destination have price data recorded within the last 7 days — stale pairs show a "Data last updated [date] — signal may be outdated" warning rather than a current-looking price
  4. Each arbitrage result row shows distance (km), travel time (hours), freight cost (Rs/quintal), spoilage estimate (%), and net expected profit (Rs/quintal) — no result omits any of these fields
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md — Backend arbitrage module (schemas, service, routes, config, main.py wiring, TDD)
- [ ] 06-02-PLAN.md — Frontend arbitrage dashboard (service client, page, Vitest tests, human verification)

## Progress

**Execution Order:**
Phases 1, 2, 3 execute sequentially. Phase 4 depends on Phase 3. Phases 5 and 6 can execute in parallel after Phase 4 completes.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. District Harmonisation + Price Cleaning | 3/3 | Complete   | 2026-03-02 |
| 2. Seasonal Price Calendar | 0/2 | Not started | - |
| 3. Feature Engineering Foundation | 2/2 | Complete   | 2026-03-03 |
| 4. XGBoost Forecasting + Serving | 0/5 | Not started | - |
| 5. Soil Crop Advisor | 2/2 | Complete    | 2026-03-03 |
| 6. Mandi Arbitrage Dashboard | 0/2 | Not started | - |
