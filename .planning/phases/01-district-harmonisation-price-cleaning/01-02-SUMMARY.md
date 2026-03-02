---
phase: 01-district-harmonisation-price-cleaning
plan: 02
subsystem: ml-data-pipeline
tags: [price-cleaning, iqr-winsorisation, pandas, alembic, parquet, outlier-detection]

# Dependency graph
requires:
  - b1c2d3e4f5a6 (district_name_map migration from Plan 01-01)
  - agmarknet_daily_10yr.parquet (25M rows, pyarrow==17.0.0)
provides:
  - price_bounds PostgreSQL table with 314 rows (one per commodity)
  - backend/scripts/clean_prices.py (IQR winsorisation pipeline)
  - backend/tests/test_clean_prices.py (14 unit tests, 100% pass)
  - Alembic migration c2d3e4f5a6b7 (chains from b1c2d3e4f5a6)
affects:
  - Phase 2 seasonal calendar (uses price_bounds at feature read time)
  - Phase 3 ML feature engineering (winsorised prices as inputs)
  - Phase 4 XGBoost model (lower_cap/upper_cap used at inference time)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-commodity IQR winsorisation: lower=max(0, Q1-3*IQR), upper=Q3+3*IQR
    - Explicit groupby loop pattern for pandas 2.x groupby compatibility (avoids MultiIndex from apply)
    - ON CONFLICT (commodity) DO UPDATE upsert for idempotent DB writes
    - Parquet column projection (3 cols from 25M rows) for memory-efficient loading
    - Immutable pipeline: original price_modal values never modified; bounds stored separately

key-files:
  created:
    - backend/alembic/versions/c2d3e4f5a6b7_add_price_bounds.py
    - backend/scripts/clean_prices.py
    - backend/tests/test_clean_prices.py
  modified: []

key-decisions:
  - "Explicit groupby loop used instead of groupby().apply() returning pd.Series: pandas 2.x produces MultiIndex Series (not DataFrame) from apply() when returning a Series, causing KeyError on column access. Explicit loop produces correct dict-of-rows DataFrame."
  - "IQR multiplier stays at 3x as planned: captures unit-corruption outliers (Guar CV 23,284%) without capping legitimate high prices in premium commodities like Coconut (upper_cap=22,500)"
  - "price_history.modal_price is never modified: bounds are stored in price_bounds table; downstream code clips prices at read time — full audit trail preserved"

requirements-completed: [HARM-02]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 1 Plan 02: Price Cleaning Pipeline Summary

**price_bounds table populated with 314 rows via per-commodity IQR winsorisation (lower=max(0,Q1-3*IQR), upper=Q3+3*IQR) — 204,003 outlier rows flagged (0.81%), Guar (CV 23,284%) and Cumin Seed (CV 22,214%) confirmed captured, price_history.modal_price untouched**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T11:45:16Z
- **Completed:** 2026-03-02T11:49:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `price_bounds` table created via Alembic migration c2d3e4f5a6b7 (chaining from b1c2d3e4f5a6), with 11 columns and UNIQUE constraint on `commodity`
- `clean_prices.py` script reads 3 columns from the 25M-row price parquet, computes per-commodity IQR bounds, flags 204,003 outlier rows (0.81%), and upserts 314 rows into price_bounds
- All 314 commodities have non-negative lower_cap (no negative price caps)
- Known corrupt commodities confirmed: Guar (395 outliers, CV 23,284%), Cumin Seed/Jeera (1,790 outliers, CV 22,214%), Bajra (222 outliers, CV 9,413%)
- 14 unit tests pass covering immutability, per-commodity bounds, outlier flagging, and non-negative lower_cap
- Idempotency confirmed: second script run produces same 314 rows (ON CONFLICT DO UPDATE)

## Price Bounds Summary

### Pipeline Statistics
- Total rows processed: 25,132,834
- Total commodities: 314
- Total outlier rows: 204,003 (0.812% of all rows)

### Top 10 by Outlier Count
| Commodity | Outlier Count | Total Count | Outlier % | Upper Cap |
|-----------|--------------|-------------|-----------|-----------|
| Potato | 12,265 | 967,023 | 1.3% | 4,275.00 |
| Green Chilli | 11,943 | 739,428 | 1.6% | 10,225.00 |
| Garlic | 9,491 | 381,360 | 2.5% | 24,200.00 |
| Tomato | 8,815 | 873,219 | 1.0% | 7,200.00 |
| Pomegranate | 8,269 | 315,614 | 2.6% | 15,800.00 |
| Brinjal | 8,183 | 826,093 | 1.0% | 5,800.00 |
| Apple | 6,579 | 483,069 | 1.4% | 18,710.00 |
| Onion | 5,998 | 986,456 | 0.6% | 6,595.00 |
| Radish | 5,996 | 369,773 | 1.6% | 3,683.33 |
| Ginger (Green) | 5,561 | 403,432 | 1.4% | 16,520.00 |

### Top 10 by Raw CV% (Most Volatile — Unit-Corruption Detected)
| Commodity | Raw CV% | Upper Cap | Outlier Count |
|-----------|---------|-----------|---------------|
| Guar | 23,284.7% | 10,000.00 | 395 |
| Cumin Seed (Jeera) | 22,214.9% | 38,083.34 | 1,790 |
| Bajra (Pearl Millet/Cumbu) | 9,413.2% | 4,425.00 | 222 |
| Chrysanthemum | 753.1% | 37.50 | 59 |
| Coconut | 690.7% | 22,500.00 | 1,397 |
| Hippe Seed | 383.1% | 15.00 | 3 |
| Rose (Loose) | 331.8% | 26,825.00 | 22 |
| Amaranthus | 326.1% | 7,712.50 | 484 |
| Potato | 291.5% | 4,275.00 | 12,265 |
| Astera | 274.3% | 300.00 | 155 |

## Actual Migration Revision ID

The illustrative revision ID `c2d3e4f5a6b7` from the plan was used as the actual revision ID. The migration chain is confirmed linear: `a2b3c4d5e6f7 → b1c2d3e4f5a6 → c2d3e4f5a6b7` (ignoring the pre-existing `a1b2c3d4e5f6` community alerts branch which diverges at `f9e8d7c6b5a4`).

## Immutability Confirmation

`price_history.modal_price` was **not modified**. The cleaning pipeline operates entirely on the parquet file in memory:
- `compute_commodity_bounds()` reads parquet → produces bounds DataFrame (new object)
- `flag_and_cap_outliers()` accepts df + bounds → returns NEW DataFrame with `is_outlier` and `modal_price_clean` (original df untouched)
- Only `price_bounds` table is written to the database

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration for price_bounds table** - `6fc2a0e` (feat)
2. **Task 2: Price cleaning script + unit tests (TDD green)** - `91b4c7f` (feat)

## Files Created

- `backend/alembic/versions/c2d3e4f5a6b7_add_price_bounds.py` — Alembic migration creating price_bounds with 11 columns, down_revision=b1c2d3e4f5a6
- `backend/scripts/clean_prices.py` — Price cleaning pipeline: compute_commodity_bounds(), flag_and_cap_outliers(), upsert_price_bounds(), main()
- `backend/tests/test_clean_prices.py` — 14 unit tests using synthetic DataFrames (no DB, no parquet)

## Phase 1 Completion Status

Both plans in Phase 1 are complete:
- **Plan 01-01**: district_name_map table seeded, 557/571 price districts joinable to rainfall (97.5%)
- **Plan 01-02**: price_bounds table populated, 314 commodities, outlier-corrupted rows identified and capped

**Phase 2 (Seasonal Price Calendar) can proceed.** The price_bounds table provides the persistent caps that all downstream feature engineering steps will apply at read time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pandas 2.x groupby().apply() returning pd.Series produces MultiIndex Series, not DataFrame columns**
- **Found during:** Task 2 (TDD GREEN phase — all 14 tests failed with KeyError on column names)
- **Issue:** In pandas 2.x, `df.groupby("commodity")["price_modal"].apply(fn)` where `fn` returns `pd.Series({...})` produces a MultiIndex Series (`(commodity, key)` index) rather than a DataFrame with columns. Column selection after `reset_index()` raised `KeyError: ['q1', 'q3', ...] not in index`.
- **Fix:** Replaced groupby().apply() pattern with explicit `for commodity, group in df.groupby("commodity")` loop that appends dicts to a list, then constructs the DataFrame from the list. This is pandas version-agnostic.
- **Files modified:** backend/scripts/clean_prices.py
- **Commit:** 91b4c7f (included in Task 2 commit)

**Total deviations:** 1 auto-fixed (Rule 1 — pandas API behaviour change in 2.x)
**Impact on plan:** Zero scope change. Fix was minimal (20 lines changed in compute_commodity_bounds). All 14 tests pass with the loop-based approach.

## Self-Check: PASSED

- FOUND: backend/alembic/versions/c2d3e4f5a6b7_add_price_bounds.py
- FOUND: backend/scripts/clean_prices.py
- FOUND: backend/tests/test_clean_prices.py
- FOUND: commit 6fc2a0e (feat(01-02): add price_bounds Alembic migration)
- FOUND: commit 91b4c7f (feat(01-02): price cleaning script + unit tests (TDD green))
- DB: price_bounds has 314 rows, 0 negative lower_cap rows, Guar/Cumin/Bajra all have outlier_count > 0

---
*Phase: 01-district-harmonisation-price-cleaning*
*Completed: 2026-03-02*
