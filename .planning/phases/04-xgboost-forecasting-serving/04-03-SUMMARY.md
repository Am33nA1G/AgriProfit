---
phase: 04-xgboost-forecasting-serving
plan: 03
subsystem: api
tags: [xgboost, skforecast, lru-cache, pydantic, joblib, ml-serving, forecast]

# Dependency graph
requires:
  - phase: 04-01
    provides: ForecastCache ORM model, model_training_log ORM model, ML deps (skforecast, xgboost, joblib, cachetools)

provides:
  - get_or_load_model() with LRU cache (maxsize=20) and thread-safe lazy loading from ml/artifacts/
  - ForecastResponse and ForecastPoint Pydantic models (8 required fields)
  - ForecastService.get_forecast() with cache hit, coverage check, model invoke, seasonal fallback
  - mape_to_confidence_colour() helper function
  - 7 unit tests: 3 loader tests + 4 service tests

affects:
  - 04-04 (API wiring uses ForecastService and ForecastResponse)
  - 04-05 (UI uses ForecastResponse shape for chart rendering)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - LRU cache with threading.Lock for thread-safe model serving
    - Cache-first serving: DB cache hit → coverage gate → model invoke → seasonal fallback
    - Seasonal fallback tier_label pattern for insufficient-data districts

key-files:
  created:
    - backend/app/ml/loader.py
    - backend/app/forecast/__init__.py
    - backend/app/forecast/schemas.py
    - backend/app/forecast/service.py
    - backend/tests/test_ml_loader.py
    - backend/tests/test_forecast_service.py
  modified: []

key-decisions:
  - "ARTIFACTS_DIR resolves as repo_root/ml/artifacts/ via Path(__file__).resolve() — 4 parent levels up from loader.py"
  - "MIN_DAYS_SERVE=365: districts with fewer than 365 days of price history always receive seasonal average fallback"
  - "mape_to_confidence_colour thresholds: <10% Green, 10-25% Yellow, >=25% or None Red"
  - "_get_coverage_days uses min/max date span not COUNT(DISTINCT date) for efficiency on 25M row table"

patterns-established:
  - "ML serving pattern: LRUCache + threading.Lock for model loading, def route handlers (not async def) to avoid event loop blocking"
  - "Fallback tier pattern: tier_label field distinguishes full model vs seasonal average fallback in all responses"

requirements-completed: [FORE-04, FORE-05, SERV-02, SERV-03]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 04 Plan 03: ML Serving Core Summary

**Thread-safe LRU model loader (cachetools) + ForecastService with cache-first lookup, coverage gate, model invocation, and seasonal fallback — 7 unit tests all passing**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T07:48:00Z
- **Completed:** 2026-03-03T07:53:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- LRU model loader with threading.Lock, lazy disk loading via joblib, ARTIFACTS_DIR constant, and get_model_cache() monitoring hook
- ForecastResponse (8 required fields) and ForecastPoint Pydantic schemas for API + chart rendering
- ForecastService with 4-step priority: DB cache hit, coverage check (365-day gate), model invocation, seasonal fallback
- mape_to_confidence_colour() mapping MAPE floats to Green/Yellow/Red UI indicators
- 7 unit tests: missing artifact returns None, lazy load + cache hit, LRU eviction with maxsize=2, schema field validation, low-coverage fallback, cache hit without model call, confidence colour mapping

## Task Commits

Each task was committed atomically:

1. **Task 1: LRU model loader with unit tests** - `ea69926` (feat)
2. **Task 2: ForecastService + Pydantic schemas with unit tests** - `8a05270` (feat)

## Files Created/Modified
- `backend/app/ml/loader.py` - get_or_load_model() LRU cache, ARTIFACTS_DIR, get_model_cache() monitor hook
- `backend/app/forecast/__init__.py` - Package marker
- `backend/app/forecast/schemas.py` - ForecastResponse (8 fields), ForecastPoint Pydantic models
- `backend/app/forecast/service.py` - ForecastService, mape_to_confidence_colour(), seasonal fallback
- `backend/tests/test_ml_loader.py` - 3 loader unit tests (missing/lazy/eviction)
- `backend/tests/test_forecast_service.py` - 4 service unit tests (schema/fallback/cache/colour)

## Decisions Made
- ARTIFACTS_DIR resolves as `repo_root/ml/artifacts/` via `Path(__file__).resolve().parent.parent.parent.parent` (4 levels up from backend/app/ml/loader.py)
- MIN_DAYS_SERVE=365: districts with fewer days always get seasonal fallback — prevents poor-quality forecasts from thin data
- mape_to_confidence_colour thresholds: <10%=Green, 10-25%=Yellow, >=25% or None=Red (matches research spec)
- _get_coverage_days uses min/max date span (not COUNT DISTINCT) — more efficient on 25M row price_history table

## Deviations from Plan

None - plan executed exactly as written. All files were already implemented and tests passing.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ML serving core complete: loader.py, schemas.py, service.py, and all unit tests pass
- Plan 04-04 (API wiring) can now import ForecastService and ForecastResponse and mount the /forecast endpoint
- Plan 04-05 (UI) can use ForecastResponse schema shape for chart rendering
- No blockers

---
*Phase: 04-xgboost-forecasting-serving*
*Completed: 2026-03-03*
