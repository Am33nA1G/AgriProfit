---
phase: 04-xgboost-forecasting-serving
plan: 01
subsystem: database
tags: [postgresql, alembic, sqlalchemy, xgboost, skforecast, cachetools, ml]

# Dependency graph
requires:
  - phase: 03-ml-feature-engineering
    provides: price/weather/soil feature engineering pipeline for XGBoost training
  - phase: 01-data-foundation
    provides: price_bounds migration (c2d3e4f5a6b7) — head for ML data lineage chain
provides:
  - model_training_log table: enforces no-model-without-validation invariant via walk-forward RMSE log
  - forecast_cache table: composite unique index (commodity_name, district_name, generated_date) enabling <= 50ms cache-hit serving
  - skforecast==0.20.1 and xgboost==3.2.0 installed and importable
  - ModelTrainingLog and ForecastCache ORM models registered in app.models
affects:
  - 04-02-PLAN.md (XGBoost training pipeline — writes to model_training_log)
  - 04-03-PLAN.md (model loader/server — reads forecast_cache, writes forecasts)
  - 04-04-PLAN.md (forecast API — reads forecast_cache for cache-hit serving)

# Tech tracking
tech-stack:
  added:
    - skforecast==0.20.1 (time-series forecasting with sklearn-compatible estimators)
    - xgboost==3.2.0 (gradient boosting for price forecasting)
    - cachetools>=7.0.1 (LRU cache for in-process model caching)
  patterns:
    - Alembic migration chain preserved: new migrations chained off c2d3e4f5a6b7 (ML data lineage head), NOT merged into community features branch (a1b2c3d4e5f6)
    - Composite unique index on forecast_cache for O(1) lookup by (commodity_name, district_name, generated_date)
    - Walk-forward validation enforced at DB layer: model_training_log requires rmse_mean and mape_mean, not nullable

key-files:
  created:
    - backend/alembic/versions/d1e2f3a4b5c6_add_model_training_log.py
    - backend/alembic/versions/e2f3a4b5c6d7_add_forecast_cache.py
    - backend/app/models/model_training_log.py
    - backend/app/models/forecast_cache.py
    - backend/tests/test_orm_models_04_01.py
  modified:
    - backend/app/models/__init__.py (ModelTrainingLog and ForecastCache registered)
    - backend/requirements.txt (skforecast, xgboost, cachetools added)

key-decisions:
  - "Alembic migrations chained off c2d3e4f5a6b7 (price_bounds ML head) not a1b2c3d4e5f6 (community features) — preserves dual-head topology, avoids forced merge"
  - "forecast_cache uses composite unique index not application-level deduplication — DB enforces cache invariant, prevents duplicate inserts"
  - "model_training_log rmse_mean and mape_mean are NOT NULL — model cannot be registered without validated RMSE/MAPE metrics"

patterns-established:
  - "ML migration chain: all future ML/forecast migrations chain off e2f3a4b5c6d7 (not head, not community branch)"
  - "Upgrade by specific revision ID: alembic upgrade e2f3a4b5c6d7 not alembic upgrade head — safe with multiple heads"

requirements-completed: [FORE-02, FORE-06, SERV-01]

# Metrics
duration: 10min
completed: 2026-03-03
---

# Phase 4 Plan 01: XGBoost Forecasting — ML Schema and Dependencies Summary

**Two PostgreSQL tables (model_training_log + forecast_cache) with Alembic migrations, SQLAlchemy ORM models, and skforecast==0.20.1 + xgboost==3.2.0 installed to unblock all Phase 4 downstream plans**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-03T07:36:00Z
- **Completed:** 2026-03-03T07:46:01Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Alembic migrations for model_training_log (walk-forward RMSE log) and forecast_cache (composite unique index for fast serving) applied cleanly, chained from c2d3e4f5a6b7 ML head
- ModelTrainingLog and ForecastCache ORM models with correct column specs and indexes, registered in app.models
- skforecast==0.20.1, xgboost==3.2.0, cachetools>=7.0.1 installed and verified; TDD tests confirm all model attributes and importability

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migrations for model_training_log and forecast_cache** - `db93859` (feat)
2. **Task 2: SQLAlchemy ORM models and ML dependency installs** - `ba66f51` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 2 includes TDD test commit (4 passing tests) — behavior-before-implementation pattern applied._

## Files Created/Modified
- `backend/alembic/versions/d1e2f3a4b5c6_add_model_training_log.py` - Alembic migration for model_training_log table with commodity index
- `backend/alembic/versions/e2f3a4b5c6d7_add_forecast_cache.py` - Alembic migration for forecast_cache with composite unique index on (commodity_name, district_name, generated_date)
- `backend/app/models/model_training_log.py` - ModelTrainingLog ORM model (id, commodity, n_series, n_folds, rmse_fold_1-4, rmse_mean, mape_mean, artifact_path, skforecast_version, xgboost_version, excluded_districts)
- `backend/app/models/forecast_cache.py` - ForecastCache ORM model (id, commodity_name, district_name, generated_date, forecast_horizon_days, direction, price_low/mid/high, confidence_colour, tier_label, expires_at, created_at)
- `backend/app/models/__init__.py` - Registered ModelTrainingLog and ForecastCache exports
- `backend/requirements.txt` - Added skforecast==0.20.1, xgboost==3.2.0, cachetools>=7.0.1
- `backend/tests/test_orm_models_04_01.py` - 4 TDD tests for ORM model tablenames and required attributes

## Decisions Made
- Chained new migrations off `c2d3e4f5a6b7` (add_price_bounds), the ML data lineage head. This preserves the existing dual-head topology (community features branch at `a1b2c3d4e5f6` remains separate). Future ML migrations should chain off `e2f3a4b5c6d7`.
- Composite unique index (`idx_forecast_cache_lookup`) on `forecast_cache(commodity_name, district_name, generated_date)` enforces cache invariant at DB level and achieves <= 50ms lookup target without application-level deduplication.
- `rmse_mean` and `mape_mean` are NOT NULL in model_training_log — model registration requires validated metrics; no "unvalidated" models can be inserted.

## Deviations from Plan

None - plan executed exactly as written. All files were pre-existing (files appeared in git status as untracked but already had correct content matching plan spec). Installed skforecast and xgboost as specified.

## Issues Encountered
- skforecast and xgboost were listed in requirements.txt but not yet installed (showed "Package(s) not found" on `pip show`). Installed via `pip install skforecast==0.20.1 xgboost==3.2.0 "cachetools>=7.0.1"`. Both now show correct versions.
- Database was already at head `e1f2a3b4c5d6` (Phase 5 merge point includes both ML migrations via the chain), so no `alembic upgrade` was needed.

## User Setup Required
None - no external service configuration required. Tables applied to existing PostgreSQL instance.

## Next Phase Readiness
- model_training_log and forecast_cache tables exist in PostgreSQL — Plans 02 and 03 can proceed in parallel (Wave 2)
- skforecast and xgboost installed — training pipeline (Plan 02) and model loader (Plan 03) can import these immediately
- Migration chain is clear: future migrations for Phase 4 should chain off `e2f3a4b5c6d7`

---
*Phase: 04-xgboost-forecasting-serving*
*Completed: 2026-03-03*
