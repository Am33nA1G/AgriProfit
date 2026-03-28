---
phase: 04-xgboost-forecasting-serving
plan: 04
subsystem: api
tags: [fastapi, apscheduler, xgboost, forecast, cron, lru-cache]

# Dependency graph
requires:
  - phase: 04-03
    provides: ForecastService, get_model_cache(), ForecastResponse schema, LRU loader
  - phase: 04-02
    provides: train_xgboost.py, ml/artifacts/ directory, model_training_log table
provides:
  - GET /api/v1/forecast/{commodity}/{district} endpoint registered and tested
  - CronTrigger(hour=3, minute=0) nightly forecast cache refresh job in APScheduler
  - app.state.model_cache attached at startup via get_model_cache()
  - Integration tests for forecast endpoint (4 tests) and scheduler job (2 tests)
affects:
  - 04-05 (frontend forecast page reads GET /api/v1/forecast/{commodity}/{district})

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "def (not async def) for route handlers that call joblib.load — avoids event loop blocking (FastAPI threadpool)"
    - "replace_existing=True on all APScheduler add_job calls — prevents job duplication on restart"
    - "CronTrigger(hour=3, minute=0) for nightly cache refresh — runs 2h after price sync at 01:00"

key-files:
  created:
    - backend/app/forecast/routes.py
    - backend/tests/test_forecast_api.py
    - backend/tests/test_scheduler.py
  modified:
    - backend/app/main.py
    - backend/app/integrations/scheduler.py

key-decisions:
  - "Route handler uses def not async def — get_or_load_model calls joblib.load (disk I/O); FastAPI runs def handlers in threadpool, avoiding event loop block (same pattern as OSRM routing handler)"
  - "horizon constrained to 7-14 via Query(ge=7, le=14) — FORE-03 requirement; values outside range return 422"
  - "forecast_ml_router alias used to avoid name collision with existing forecasts_router (app/forecasts/routes.py)"
  - "refresh_forecast_cache_job only refreshes entries where expires_at < now() — incremental refresh, not full regeneration"

patterns-established:
  - "Scheduler job registration: add_job with replace_existing=True is idempotent across app restarts"
  - "Route files import ForecastService directly — no dependency injection for service layer, only for DB session"

requirements-completed: [FORE-03, FORE-06, SERV-01, SERV-04]

# Metrics
duration: 12min
completed: 2026-03-03
---

# Phase 4 Plan 04: Forecast API Serving Summary

**FastAPI GET /api/v1/forecast/{commodity}/{district} wired with LRU model cache on app.state and APScheduler nightly refresh job at 03:00 — all 6 integration tests passing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-03T13:20:00Z
- **Completed:** 2026-03-03T13:32:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- GET /api/v1/forecast/{commodity}/{district} endpoint registered at /api/v1 prefix with horizon=7|14 constraint
- APScheduler extended with CronTrigger(hour=3, minute=0) nightly forecast cache refresh job (id="refresh_forecast_cache", replace_existing=True)
- app.state.model_cache attached to LRU cache from get_model_cache() during lifespan startup
- 6 tests passing: 4 API integration tests (endpoint registered, 14-day schema, cache hit, fallback tier) and 2 scheduler unit tests (job registered, idempotent)

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI forecast router and integration tests** - `7ab69af` (feat)
2. **Task 2: Wire router into main.py, attach model cache, extend scheduler** - `c73d339` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/app/forecast/routes.py` - FastAPI router: GET /{commodity}/{district}, def handler, horizon Query param 7-14
- `backend/app/main.py` - forecast_ml_router registered at /api/v1; get_model_cache() attached to app.state in lifespan
- `backend/app/integrations/scheduler.py` - refresh_forecast_cache_job() added, CronTrigger(hour=3, minute=0), replace_existing=True
- `backend/tests/test_forecast_api.py` - 4 integration tests: endpoint registered, schema shape, cache hit, fallback tier_label
- `backend/tests/test_scheduler.py` - 2 unit tests: nightly job registered with correct trigger, idempotent registration

## Decisions Made

- Route handler uses `def` not `async def` — joblib.load is blocking disk I/O; FastAPI runs sync handlers in a threadpool, avoiding event loop blocking (same pattern as OSRM routing handler documented in MEMORY.md)
- `forecast_ml_router` alias used instead of `forecast_router` — prevents name collision with the existing `forecasts_router` (legacy `app/forecasts/routes.py`)
- `refresh_forecast_cache_job` only refreshes entries where `expires_at < now()` — incremental refresh avoids regenerating all pairs nightly, only stale ones

## Deviations from Plan

None - all files (routes.py, main.py updates, scheduler.py updates) were already created during plan 04-03 execution. This plan committed the test files and verified everything passes.

## Issues Encountered

None. All plan artifacts were already in place from plan 04-03 execution. Tests pass cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend forecast serving is complete: endpoint registered, cache-first path tested, nightly refresh scheduled
- Plan 04-05 (frontend forecast page) can now call GET /api/v1/forecast/{commodity}/{district} and display results
- Wave 4 begins: frontend forecast UI reads the new endpoint

---
*Phase: 04-xgboost-forecasting-serving*
*Completed: 2026-03-03*
