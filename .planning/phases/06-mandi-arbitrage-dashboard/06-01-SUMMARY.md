---
phase: 06-mandi-arbitrage-dashboard
plan: 01
subsystem: api
tags: [fastapi, pydantic, arbitrage, transport, freshness-gate, margin-threshold]

requires:
  - phase: 04-transport-logistics-engine
    provides: compare_mandis(), MandiComparison schema, price analytics with latest_price_date

provides:
  - GET /api/v1/arbitrage/{commodity}/{district} endpoint returning ArbitrageResponse
  - ArbitrageResult and ArbitrageResponse Pydantic schemas (arbitrage/schemas.py)
  - get_arbitrage_results() service with 7-day freshness gate, margin threshold, top-3 ranking
  - latest_price_date field on MandiComparison (backward-compatible addition)
  - arbitrage_margin_threshold_pct config setting (default 10%)
  - 18 new tests (11 service unit tests + 7 integration tests)

affects:
  - 06-mandi-arbitrage-dashboard Plan 02 (frontend dashboard consuming this API)

tech-stack:
  added: []
  patterns:
    - Sync route handler (def not async def) — OSRM blocks event loop, must run in thread pool
    - Per-quintal normalisation: compare_mandis() called with quantity_kg=100 so costs.total_cost IS the per-quintal cost directly
    - data_reference_date = MAX(latest_price_date) from returned mandis, NEVER date.today()
    - Stale-but-included pattern: is_stale=True results remain in results[], only suppressed by margin threshold

key-files:
  created:
    - backend/app/arbitrage/__init__.py
    - backend/app/arbitrage/schemas.py
    - backend/app/arbitrage/service.py
    - backend/app/arbitrage/routes.py
    - backend/tests/test_arbitrage_service.py
    - backend/tests/test_arbitrage_api.py
  modified:
    - backend/app/transport/schemas.py (added latest_price_date to MandiComparison)
    - backend/app/transport/service.py (populate latest_price_date from price_analytics_map)
    - backend/app/core/config.py (arbitrage_margin_threshold_pct setting)
    - backend/app/main.py (arbitrage_router import, tag metadata, include_router)

key-decisions:
  - "freight_cost_per_quintal = costs.total_cost directly: compare_mandis() is called with quantity_kg=100 (1 quintal), so costs.total_cost IS already the per-quintal cost — no further division"
  - "Stale results are INCLUDED in results with is_stale=True — they are NOT silently dropped; only margin-threshold failures are suppressed"
  - "data_reference_date = MAX(latest_price_date) from returned mandis; DB fallback only when ALL price dates are None"
  - "Route handler is def (not async def) to avoid OSRM event-loop blocking — FastAPI runs sync handlers in thread pool"
  - "Freshness boundary is strictly > 7 days (days_since_update > 7), not >= 7"
  - "TDD test fix: reference date must be one of the RETURNED mandi dates — test must set the fresh anchor mandi to ref_date so it drives data_reference_date"

patterns-established:
  - "Arbitrage module pattern: schemas.py + service.py + routes.py with sync def handler"
  - "Freshness relative to MAX(price_date) in dataset — all data freshness checks use this pattern"
  - "Margin threshold = (net_profit / gross_revenue) * 100 >= threshold_pct"

requirements-completed: [ARB-01, ARB-02, ARB-03, ARB-04]

duration: 7min
completed: 2026-03-03
---

# Phase 06 Plan 01: Mandi Arbitrage Dashboard Backend Summary

**GET /api/v1/arbitrage/{commodity}/{district} endpoint with 7-day freshness gate, 10% margin threshold, and top-3 ranking via existing transport engine**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-03T01:45:25Z
- **Completed:** 2026-03-03T01:52:XX Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- Built complete arbitrage module (schemas, service, routes) wired into existing transport engine
- Implemented 7-day freshness gate using MAX(price_date) as reference — stale results flagged but not dropped
- 10% net margin threshold filters low-value signals; suppressed_count returned for transparency
- 18 new tests (11 unit + 7 integration) all pass GREEN; 30 transport tests remain GREEN (backward compat)

## Task Commits

1. **Task 1: Add schemas and failing tests (RED)** - `e98d802` (test)
2. **Task 2: Implement arbitrage service (GREEN)** - `1734a2f` (feat)
3. **Task 3: Routes, main.py registration, integration tests** - `8127c18` (feat)

## Files Created/Modified

- `backend/app/arbitrage/__init__.py` — Package init (empty)
- `backend/app/arbitrage/schemas.py` — ArbitrageResult and ArbitrageResponse Pydantic v2 models
- `backend/app/arbitrage/service.py` — get_arbitrage_results() with freshness, threshold, ranking logic
- `backend/app/arbitrage/routes.py` — GET /arbitrage/{commodity}/{district} FastAPI route (sync def)
- `backend/tests/test_arbitrage_service.py` — 11 unit tests: schema validation + service behaviour
- `backend/tests/test_arbitrage_api.py` — 7 integration tests via TestClient
- `backend/app/transport/schemas.py` — Added latest_price_date to MandiComparison (backward-compatible)
- `backend/app/transport/service.py` — Populate latest_price_date from price_analytics_map in compare_mandis()
- `backend/app/core/config.py` — arbitrage_margin_threshold_pct setting (default 10%, range 0-50%)
- `backend/app/main.py` — Import arbitrage_router, add "Arbitrage" tag metadata, include_router

## Decisions Made

- **freight_cost_per_quintal calculation:** `costs.total_cost` directly (no division) because `compare_mandis()` is called with `quantity_kg=100` (1 quintal normalisation), so `costs.total_cost` already represents the per-quintal cost.
- **Stale-but-included semantics:** Mandis with `days_since_update > 7` appear in results with `is_stale=True` and `stale_warning` populated. Only the margin threshold causes suppression — staleness never silently drops a result.
- **Reference date is MAX of returned mandi dates:** Not `date.today()`, not a DB query (unless all price dates are None). This is fast and uses the same data freshness model as the rest of the transport engine.
- **Sync route handler:** Route handler is `def` (not `async def`) per the established OSRM blocking protection pattern from the transport module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TDD test reference-date assumption**
- **Found during:** Task 2 (implementing service, running tests)
- **Issue:** `test_7day_freshness_gate` and `test_stale_results_have_warning` assumed a `ref_date` constant but the service computes `data_reference_date = max(latest_price_dates)` from returned mandis. When the "fresh" mandi had `fresh_date = ref_date - 3 days`, the computed reference date was `fresh_date`, making the "stale" mandi only 7 days old (not > 7).
- **Fix:** Updated tests to set the fresh anchor mandi to `latest_price_date=ref_date` (so it drives the reference date). For the warning test, added a fresh anchor mandi to establish the reference date, then verified the stale mandi's warning.
- **Files modified:** `backend/tests/test_arbitrage_service.py`
- **Committed in:** `1734a2f` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug in test logic)
**Impact on plan:** Fix was necessary for test correctness. Service logic is correct per spec; tests needed to match how the service actually computes the reference date.

## Issues Encountered

- Pre-existing test failures in `test_prices_api.py` and `test_users_api.py` (SQLite schema mismatch: "table users has no column named name", "table commodities has no column named description") — out of scope, pre-date this plan's changes.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Backend arbitrage API is complete and ready for frontend consumption
- Plan 02 frontend dashboard can now target `GET /api/v1/arbitrage/{commodity}/{district}`
- Response shape is fully documented in `ArbitrageResponse` schema
- `threshold_pct` is configurable via `ARBITRAGE_MARGIN_THRESHOLD_PCT` env var (default 10)

## Self-Check: PASSED

All created files exist. All 3 task commits exist (e98d802, 1734a2f, 8127c18). Config setting `arbitrage_margin_threshold_pct = 10.0` confirmed.

---
*Phase: 06-mandi-arbitrage-dashboard*
*Completed: 2026-03-03*
