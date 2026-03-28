---
phase: 02-seasonal-price-calendar
plan: 01
subsystem: database
tags: [pandas, parquet, alembic, postgresql, aggregation, seasonal]

# Dependency graph
requires:
  - phase: 01-district-harmonisation-price-cleaning
    provides: price_bounds table with per-commodity lower_cap/upper_cap for outlier clipping
provides:
  - seasonal_price_stats table in PostgreSQL with UNIQUE(commodity_name, state_name, month)
  - Pure aggregator module: load_and_prepare(), compute_seasonal_stats(), upsert_seasonal_stats()
  - Offline pipeline script train_seasonal.py that reduces 25M rows to ~135K summary rows
  - 10 unit tests for compute_seasonal_stats() verifying is_best/is_worst labelling rules
affects:
  - 02-02-seasonal-api (FastAPI endpoint that queries seasonal_price_stats directly)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit for-loop over groupby() for pandas 2.x safety (not groupby().apply())"
    - "Pure function compute_seasonal_stats() — no DB/IO, fully unit-testable without running DB"
    - "Offline aggregation pipeline: parquet -> pandas -> PostgreSQL upsert"

key-files:
  created:
    - backend/alembic/versions/d3e4f5a6b7c8_add_seasonal_price_stats.py
    - backend/app/ml/seasonal/__init__.py
    - backend/app/ml/seasonal/aggregator.py
    - backend/scripts/train_seasonal.py
    - backend/tests/test_seasonal.py
  modified: []

key-decisions:
  - "compute_seasonal_stats() is a pure function — no DB calls inside function body; only load_and_prepare() and upsert_seasonal_stats() handle I/O"
  - "is_best/is_worst labels only set when years_of_data >= 3 — sparse series never get best/worst to avoid misleading farmers"
  - "month_rank=1 means highest median_price (rank descending by price)"
  - "Explicit for-loop over groupby() (not apply()) for pandas 2.x compatibility per STATE.md"
  - "train_seasonal.py is not run during plan execution — requires live PostgreSQL with price_bounds and 25M row parquet"

patterns-established:
  - "Offline aggregation: read parquet -> apply DB-sourced caps -> pure compute -> upsert"
  - "Pure aggregator pattern: separate I/O functions (load_and_prepare, upsert) from pure compute (compute_seasonal_stats)"

requirements-completed: [SEAS-01, SEAS-02, SEAS-03, SEAS-04]

# Metrics
duration: 15min
completed: 2026-03-03
---

# Phase 2 Plan 01: Seasonal Price Calendar — Aggregation Pipeline Summary

**PostgreSQL seasonal_price_stats table + pure pandas aggregator reducing 25M price rows to ~135K monthly medians with outlier capping, is_best/is_worst labels (only when years_of_data >= 3), and 10 passing unit tests**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-03T07:13:44Z
- **Completed:** 2026-03-03T07:28:00Z
- **Tasks:** 3
- **Files created:** 5

## Accomplishments
- Alembic migration creates seasonal_price_stats with UNIQUE(commodity_name, state_name, month) and idx_seasonal_commodity_state index; applied successfully to running DB
- Pure aggregator module (aggregator.py) with load_and_prepare() + compute_seasonal_stats() + upsert_seasonal_stats(); compute function has zero DB/IO calls
- 10 unit tests all pass GREEN covering: low-data no-label case, sufficient-data labelling, month_rank correctness, IQR formula, empty DataFrame, mixed-commodity independence
- train_seasonal.py offline pipeline script follows clean_prices.py pattern exactly with [1/4]–[4/4] progress steps and spot-check queries for Onion/Maharashtra and Tomato/West Bengal

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration for seasonal_price_stats** - `45e5b7b` (feat)
2. **Task 2: Pure aggregator module + unit tests (TDD)** - `0cdaf56` (feat)
3. **Task 3: train_seasonal.py aggregation script** - `3240b98` (feat)

## Files Created/Modified
- `backend/alembic/versions/d3e4f5a6b7c8_add_seasonal_price_stats.py` - Migration with all 14 columns, UNIQUE constraint, index, idempotent upgrade/downgrade
- `backend/app/ml/seasonal/__init__.py` - Empty package init
- `backend/app/ml/seasonal/aggregator.py` - load_and_prepare(), compute_seasonal_stats(), upsert_seasonal_stats()
- `backend/scripts/train_seasonal.py` - Full offline pipeline: parquet load -> compute -> upsert -> spot-check
- `backend/tests/test_seasonal.py` - 10 unit tests for pure compute_seasonal_stats(), no DB required

## Decisions Made
- compute_seasonal_stats() designed as a pure function so unit tests require no DB setup — only load_and_prepare() touches the DB (reads price_bounds)
- is_best=True for top-2 months, is_worst=True for bottom-1 month — only when years_of_data >= 3; sparse series always get False
- Explicit for-loop over groupby() used throughout aggregator.py for pandas 2.x compatibility (groupby().apply() creates MultiIndex in pandas 2.x)
- train_seasonal.py not executed during plan — requires live PostgreSQL + 25M row parquet; script validated via ast.parse() syntax check only

## Deviations from Plan

None — all three files already existed on disk from a prior session and were substantively correct. Verified each file against plan spec, found them complete and conformant. Ran all verifications (migration applies cleanly, 10/10 tests pass, syntax check passes, import works without DB). Committed the pre-existing files as three task-based commits per plan protocol.

## Issues Encountered
- Files were pre-existing from a prior partial session — no code writing was needed. Verified correctness by running all verifications before committing.

## User Setup Required

None — no external service configuration required for the aggregation module itself.

**Post-plan manual step (not automated):** Run `python backend/scripts/train_seasonal.py` after Phase 1 price_bounds are seeded to populate seasonal_price_stats. Expected runtime 3-8 minutes. Spot-check output should show Onion peaking Oct-Nov in Maharashtra, Tomato peaking Jul in West Bengal.

## Next Phase Readiness
- seasonal_price_stats table exists in DB and is ready for FastAPI queries (Plan 02)
- compute_seasonal_stats() exports are stable — Plan 02 can import from app.ml.seasonal.aggregator
- train_seasonal.py must be run manually before Plan 02 endpoint returns data

---
*Phase: 02-seasonal-price-calendar*
*Completed: 2026-03-03*
