---
phase: 03-feature-engineering-foundation
plan: 01
subsystem: ml
tags: [pandas, numpy, price-features, rainfall-features, anti-leakage, tdd]

# Dependency graph
requires:
  - phase: 01-district-harmonisation
    provides: harmonised district names for cross-dataset joins
provides:
  - compute_price_features() with cutoff_date enforcement and daily reindex
  - compute_longterm_rainfall_avg() and compute_rainfall_deficit() with completeness check
  - Leakage detection test (permanent sentinel in test suite)
affects: [04-xgboost-forecasting-serving, 03-02-weather-soil-features]

# Tech tracking
tech-stack:
  added: []
  patterns: [cutoff_date enforcement via series.loc[:cutoff_date], daily reindex before shift for irregular series, shift(1) before rolling to exclude current day]

key-files:
  created:
    - backend/app/ml/price_features.py
    - backend/app/ml/rainfall_features.py
    - backend/tests/test_price_features.py
    - backend/tests/test_rainfall_features.py
  modified: []

key-decisions:
  - "Daily reindex with forward-fill before shift ensures calendar-day lags on irregular price series"
  - "shift(1) before rolling windows excludes current-day price from its own window statistics"
  - "Zero longterm rainfall avg produces NaN deficit_pct (not ZeroDivisionError) using pandas replace(0, nan)"
  - "Completeness threshold set at 10 of 12 months per district-year; 2026 partial year correctly flagged"

patterns-established:
  - "Anti-leakage pattern: cutoff_date enforced inside feature function, not by caller"
  - "Pure function pattern: feature functions accept DataFrames, return DataFrames, zero DB calls"
  - "Immutability pattern: input Series/DataFrames not modified (copy before mutation)"

requirements-completed: [FEAT-01, FEAT-02, FEAT-04]

# Metrics
duration: 6min
completed: 2026-03-08
---

# Phase 3 Plan 1: Price and Rainfall Feature Functions Summary

**Price lag/rolling-stats and rainfall deficit feature functions with TDD, daily reindex for irregular series, and permanent leakage detection sentinel test**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-08T12:22:26Z
- **Completed:** 2026-03-08T12:29:17Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- compute_price_features() handles irregular price series via daily reindex + forward-fill, with cutoff_date structurally enforced inside the function body
- compute_longterm_rainfall_avg() and compute_rainfall_deficit() with baseline year exclusion and completeness checking (>= 10 months per district-year)
- 18 unit tests passing: 9 price feature tests (including permanent leakage detection) + 9 rainfall feature tests
- Zero database calls in any feature function body -- pure DataFrame-in, DataFrame-out architecture

## Task Commits

Code was previously committed as part of the v1.0 milestone bulk commit:

1. **Task 1: Price features -- tests + implementation** - `57f19cb0` (feat: TDD price_features.py with 9 tests)
2. **Task 2: Rainfall features -- tests + implementation** - `57f19cb0` (feat: TDD rainfall_features.py with 9 tests)
3. **Task 3: Full suite regression check** - verified, no new commit needed (all 18 feature tests pass, no regressions in ML unit tests)

**Plan metadata:** (this commit)

## Files Created/Modified

- `backend/app/ml/price_features.py` - compute_price_features() with cutoff_date enforcement, daily reindex, lag columns, rolling mean/std
- `backend/app/ml/rainfall_features.py` - compute_longterm_rainfall_avg(), compute_rainfall_deficit(), check_rainfall_completeness()
- `backend/tests/test_price_features.py` - 9 tests including leakage detection sentinel, irregular series, immutability
- `backend/tests/test_rainfall_features.py` - 9 tests including deficit formula, zero-avg NaN handling, partial year completeness

## Decisions Made

- Daily reindex with forward-fill (never backfill) ensures shift(N) operates on calendar days, not trading days
- shift(1) applied before rolling windows so current-day price is excluded from its own window statistics
- Zero longterm rainfall average produces NaN (not exception) via pandas replace(0, nan) before division
- Completeness threshold of 10 months catches 2026 partial-year data correctly

## Deviations from Plan

None - plan executed exactly as written. Code and tests matched the plan specification precisely.

## Issues Encountered

- Pre-existing database integration test failures (SQLAlchemy OperationalError on tests requiring DB connection) are not caused by this plan's changes. These are out of scope -- only ML unit tests were verified for regression.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Price and rainfall feature functions ready for consumption by Phase 4 XGBoost training scripts
- Phase 3 Plan 2 (weather + soil features) can proceed independently
- All feature functions follow the pure-function pattern (DataFrame in, DataFrame out) established here

## Self-Check: PASSED

- All 5 files verified present on disk
- Commit 57f19cb0 verified in git history
- 18/18 tests pass (pytest exit code 0)
- No database calls in feature function bodies (grep verified)

---
*Phase: 03-feature-engineering-foundation*
*Completed: 2026-03-08*
