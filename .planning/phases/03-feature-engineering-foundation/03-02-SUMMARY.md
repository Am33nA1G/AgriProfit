---
phase: 03-feature-engineering-foundation
plan: 02
subsystem: ml
tags: [pandas, weather, soil, feature-engineering, tdd, pure-functions]

# Dependency graph
requires:
  - phase: 01-district-harmonisation-price-cleaning
    provides: "district_name_map table with canonical district names and tier classification"
provides:
  - "compute_weather_features() pure function with Tier A+/B split and cutoff_date enforcement"
  - "compute_soil_features() pure function for block-level NPK/OC/pH profile extraction"
  - "WEATHER_FEATURE_COLS constant (5 weather columns)"
  - "SOIL_NUTRIENT_COLS constant (15 soil nutrient columns)"
affects: [04-xgboost-forecasting-serving, 05-soil-crop-advisor]

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-function-feature-engineering, tier-based-district-split, percentage-string-parsing]

key-files:
  created:
    - backend/app/ml/weather_features.py
    - backend/app/ml/soil_features.py
    - backend/tests/test_weather_features.py
    - backend/tests/test_soil_features.py
  modified: []

key-decisions:
  - "Tier B districts get empty DataFrame (0 rows), not NaN-filled rows -- XGBoost handles NaN natively, imputing would create false signal for ~310 districts"
  - "Soil features accept pre-loaded DataFrame as input -- zero file reads inside function body, enabling pure-function testing with synthetic data"
  - "Missing nutrients in soil data return empty DataFrame rather than partial/NaN-filled row -- ensures data integrity downstream"

patterns-established:
  - "Pure function pattern: all feature functions accept DataFrames in, return DataFrames out, no DB calls inside"
  - "Tier A+/B split: weather features present for ~261 harmonised districts, absent for ~310 others"
  - "Percentage string parsing: soil CSV values like '92%' stripped and converted to float"

requirements-completed: [FEAT-03, FEAT-04]

# Metrics
duration: 8min
completed: 2026-03-08
---

# Phase 3 Plan 02: Weather + Soil Feature Functions Summary

**Pure weather Tier A+/B split and soil NPK/OC/pH block profile extraction with 15 TDD tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-08T12:22:31Z
- **Completed:** 2026-03-08T12:30:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Weather feature function with Tier A+/B district split: 261 Tier A+ districts get 5 weather columns, ~310 Tier B districts get empty DataFrame (not imputed values)
- Soil feature function extracts 15-column NPK/OC/pH profile from pre-loaded block DataFrames with percentage string parsing
- 15 TDD tests covering all edge cases: empty input, cutoff enforcement, immutability, column counts, incomplete nutrients

## Task Commits

Each task was committed atomically:

1. **Task 1: Weather features -- tests first, then implement compute_weather_features()** - `57f19cb0` (feat+test)
2. **Task 2: Soil features -- tests first, then implement compute_soil_features()** - `57f19cb0` (feat+test)
3. **Task 3: Full suite -- verify no regressions across all backend tests** - No new commit (verification only)

_Note: Tasks 1 and 2 were committed together in a prior session bulk commit. All 15 tests pass._

## Files Created/Modified
- `backend/app/ml/weather_features.py` - compute_weather_features() with Tier A+/B split, cutoff_date enforcement, WEATHER_FEATURE_COLS constant
- `backend/app/ml/soil_features.py` - compute_soil_features() accepting pre-loaded block DataFrame, SOIL_NUTRIENT_COLS constant (15 columns)
- `backend/tests/test_weather_features.py` - 8 tests: Tier A+ returns 5 cols, Tier B empty, cutoff enforcement, no input mutation, DatetimeIndex
- `backend/tests/test_soil_features.py` - 7 tests: nutrient cols, 15 col count, unknown block empty, None input, no mutation, values sum to 100, incomplete nutrients

## Decisions Made
- Tier B districts receive empty DataFrame (0 rows), not NaN-filled rows -- XGBoost handles NaN natively and imputing creates false signal for ~310 districts without weather data
- Soil features accept pre-loaded DataFrame as input (zero file reads inside function body) -- enables pure-function testing with synthetic data
- Missing nutrients in soil data return empty DataFrame rather than partial/NaN-filled row

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing backend test failures in API test files (test_mandis_api, test_notifications_api, test_prices_api, test_users_api) due to SQLAlchemy connection errors -- these are unrelated to feature engineering and exist because those tests require a running PostgreSQL database. All 33 feature engineering tests pass cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Weather and soil feature functions are ready for Phase 4 XGBoost training consumption
- compute_weather_features() can be called by the training script with the tier_a_plus_districts set from district_name_map
- compute_soil_features() is ready for Phase 5 Soil Crop Advisor integration
- All feature functions follow the pure-function pattern established in 03-01 (price + rainfall features)

## Self-Check: PASSED

All 4 created files verified present on disk. Commit 57f19cb0 verified in git history. All 15 tests pass (8 weather + 7 soil).

---
*Phase: 03-feature-engineering-foundation*
*Completed: 2026-03-08*
