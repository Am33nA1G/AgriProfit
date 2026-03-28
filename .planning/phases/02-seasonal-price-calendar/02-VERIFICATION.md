---
phase: 02-seasonal-price-calendar
verified: 2026-03-03T08:30:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 2: Seasonal Price Calendar Verification Report

**Phase Goal:** A farmer can select any commodity and state and see a monthly sell-window chart built from 10 years of price history, with best and worst months clearly labelled.
**Verified:** 2026-03-03T08:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

**Human Verification Note:** Human approval confirmed — chart renders with green best months, red worst months, IQR error bars, low-confidence warning banner, and coverage gap card.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can open /seasonal, select a commodity and state, and see a monthly bar chart | VERIFIED | `frontend/src/app/seasonal/page.tsx` (458 lines): useQuery + fetchSeasonalData → api.get("/seasonal"); chart renders via Recharts ComposedChart. Human verified. |
| 2 | Chart labels best months (green) and worst month (red) | VERIFIED | Cell colouring at lines 421-430: `is_best ? '#10b981' : is_worst ? '#ef4444' : '#6b7280'`. Human verified. |
| 3 | IQR error bars are rendered on each bar | VERIFIED | ErrorBar component with `dataKey="errorBar"` (line 431); errorBar computed as `[median-q1, q3-median]` (line 151). Human verified. |
| 4 | Low-confidence warning banner appears when years_of_data < 3 | VERIFIED | routes.py line 111: `low_confidence=max_years < 3`; page.tsx line 321: renders amber banner when `data.low_confidence`. Human verified. |
| 5 | Coverage gap card appears when no data (404) | VERIFIED | fetchSeasonalData throws "NOT_FOUND" on 404 (lines 56-58); page.tsx renders amber gap card at lines 290-302. Human verified. |
| 6 | Endpoint reads only from seasonal_price_stats (no price_history scan) | VERIFIED | routes.py lines 66-76: SELECT FROM seasonal_price_stats only; no price_history reference anywhere in seasonal module. |
| 7 | seasonal_price_stats table exists with UNIQUE(commodity_name, state_name, month) constraint | VERIFIED | Migration `d3e4f5a6b7c8_add_seasonal_price_stats.py` with UniqueConstraint "uq_seasonal_commodity_state_month" (line 41-44). |
| 8 | train_seasonal.py populates the table from parquet with price_bounds caps applied | VERIFIED | aggregator.py `load_and_prepare()` reads price_bounds (line 51), clips price_modal (lines 55-57). train_seasonal.py calls all three pipeline functions (lines 68, 75, 82). |
| 9 | is_best/is_worst only set when years_of_data >= 3 | VERIFIED | aggregator.py line 132: `if sorted_g["years_of_data"].iloc[0] >= 3`. Test `test_low_data_no_best_worst_labels` and `test_mixed_data_independent_labelling` both pass. |
| 10 | Unit tests for pure aggregator pass without running a database | VERIFIED | 10/10 tests pass in `backend/tests/test_seasonal.py`. All tests use synthetic DataFrames only. |
| 11 | seasonal router registered in main.py at /api/v1 prefix | VERIFIED | main.py line 53: import; line 374: `app.include_router(seasonal_router, prefix="/api/v1")`. |
| 12 | GET /api/v1/seasonal returns 404 with clear error for unknown commodity/state | VERIFIED | routes.py lines 78-86: HTTPException(status_code=404) with descriptive detail message. |
| 13 | Commodity list and state list served from DB-backed endpoints | VERIFIED | routes.py lines 20-43: `/seasonal/commodities` and `/seasonal/states` endpoints reading from seasonal_price_stats. |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/d3e4f5a6b7c8_add_seasonal_price_stats.py` | Alembic migration for seasonal_price_stats table + index | VERIFIED | Exists; 56 lines; down_revision="c2d3e4f5a6b7"; 14 columns; UNIQUE constraint; index; correct downgrade. |
| `backend/app/ml/seasonal/aggregator.py` | Pure functions: load_and_prepare(), compute_seasonal_stats(), upsert_seasonal_stats() | VERIFIED | Exists; 208 lines; all 3 functions exported; compute_seasonal_stats is a pure function (no DB/IO calls). |
| `backend/scripts/train_seasonal.py` | Offline aggregation pipeline (parquet → seasonal_price_stats) | VERIFIED | Exists; 131 lines (meets min_lines: 60); imports all 3 aggregator functions; [1/4]-[4/4] progress steps; spot-check queries. |
| `backend/tests/test_seasonal.py` | Unit tests for pure aggregator functions | VERIFIED | Exists; 191 lines (meets min_lines: 60); 10 tests; 10/10 pass. |
| `backend/app/seasonal/schemas.py` | MonthlyStatPoint and SeasonalCalendarResponse Pydantic models | VERIFIED | Exists; exports MonthlyStatPoint and SeasonalCalendarResponse; ConfigDict(from_attributes=True) on both. Note: top-level field is `total_years` (not `years_of_data` as plan specified) — frontend matches. |
| `backend/app/seasonal/routes.py` | GET /seasonal endpoint reading only from seasonal_price_stats | VERIFIED | Exists; 114 lines; exports `router`; reads only seasonal_price_stats; LOWER() case-insensitive matching; 404 on unknown pair; bonus /commodities and /states endpoints. |
| `backend/app/main.py` | seasonal router registered at /api/v1 | VERIFIED | Line 53: import; line 374: include_router at /api/v1; "Seasonal" tag in TAGS_METADATA (line 148). |
| `frontend/src/app/seasonal/page.tsx` | Seasonal calendar page with Recharts ComposedChart + IQR ErrorBar | VERIFIED | Exists; 458 lines (meets min_lines: 120); "use client"; useQuery; ComposedChart + Bar + ErrorBar + Cell; low-confidence banner; coverage gap card. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/src/app/seasonal/page.tsx` | `/api/v1/seasonal` | `api.get("/seasonal", { params: { commodity, state } })` inside fetchSeasonalData, called by useQuery | WIRED | Lines 51-54: api.get("/seasonal") with params. Response consumed at lines 137-143 via useQuery. chartData computed from response.months (line 145-160). |
| `backend/app/seasonal/routes.py` | `seasonal_price_stats` table | `db.execute(text('SELECT ... FROM seasonal_price_stats WHERE LOWER(commodity_name)=... AND LOWER(state_name)=...'))` | WIRED | Lines 66-76: db.execute with parameterised query; rows.fetchall() consumed at lines 78-113 to build response. |
| `backend/app/main.py` | `backend/app/seasonal/routes.py` | `from app.seasonal.routes import router as seasonal_router; app.include_router(seasonal_router, prefix='/api/v1')` | WIRED | Line 53: import confirmed. Line 374: include_router confirmed. |
| `backend/scripts/train_seasonal.py` | `backend/app/ml/seasonal/aggregator.py` | `from app.ml.seasonal.aggregator import load_and_prepare, compute_seasonal_stats, upsert_seasonal_stats` | WIRED | Lines 38-42: all three functions imported. Lines 68, 75, 82: all three functions called in pipeline. |
| `backend/app/ml/seasonal/aggregator.py` | `price_bounds` table | `pd.read_sql("SELECT commodity, lower_cap, upper_cap FROM price_bounds", con=engine)` | WIRED | Lines 50-53: pd.read_sql confirmed. Result merged and used to clip price_modal (lines 54-57). |
| `backend/app/ml/seasonal/aggregator.py` | `seasonal_price_stats` table | `INSERT ... ON CONFLICT (commodity_name, state_name, month) DO UPDATE SET` | WIRED | Lines 165-183: full upsert SQL. Lines 188-203: iterrows() loop executes upsert for every row. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SEAS-01 | 02-01, 02-02 | User can select any of the 314 commodities and any state and see a monthly price chart (average +/- std) aggregated over the last 10 years | SATISFIED | /seasonal page with commodity + state selectors, Recharts bar chart with median price per month, IQR error bars, served from pre-aggregated seasonal_price_stats. Human verified. |
| SEAS-02 | 02-01, 02-02 | Calendar highlights the historically cheapest and most expensive months with labels ("Best time to sell", "Avoid selling") | SATISFIED | is_best (top-2 months) and is_worst (bottom-1 month) computed in aggregator.py; Cell colouring green/red in page.tsx; summary cards "Best Months to Sell" / "Lowest Price Month". Human verified. |
| SEAS-03 | 02-01, 02-02 | Calendar shows data confidence — commodities/states with fewer than 3 years of data display a low-confidence warning | SATISFIED | low_confidence=max_years < 3 in routes.py; amber warning banner in page.tsx with year count and advisory text. Human verified. |
| SEAS-04 | 02-01 | Calendar data is pre-aggregated and served from a seasonal_price_stats table (no ad-hoc full-table scans on the 25M row price table) | SATISFIED | Alembic migration creates seasonal_price_stats; train_seasonal.py populates it offline; routes.py only queries seasonal_price_stats. |
| UI-01 | 02-02 | Seasonal price calendar page — commodity + state selector, monthly bar/line chart, best/worst month highlights | SATISFIED | page.tsx: searchable commodity dropdown backed by /seasonal/commodities, state Select backed by /seasonal/states, ComposedChart, Cell colouring for best/worst. Human verified. |
| UI-05 | 02-02 | All dashboards display coverage gap messages when a feature is unavailable for the selected region (no silent failures) | SATISFIED | Two coverage gap paths: (1) low_confidence amber banner for thin data; (2) amber gap card on 404 for missing data. Human verified. |

**All 6 phase 2 requirements satisfied.**

**Note on REQUIREMENTS.md traceability status:** REQUIREMENTS.md still shows SEAS-01, SEAS-02, SEAS-03, UI-01 as "Pending" (not checked). SEAS-04 and UI-05 are marked complete for Phase 2. The implementation is verified complete against the actual code. The REQUIREMENTS.md traceability table was not updated post-completion — this is a documentation tracking gap, not an implementation gap.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/app/seasonal/page.tsx` | 207, 250 | HTML `placeholder="..."` attributes | Info | These are standard HTML input placeholder attributes, not implementation stubs. No impact. |

No blocker or warning anti-patterns found. The three `return null` / `return []` occurrences in page.tsx (lines 78, 132, 146) are legitimate guard returns in the CustomTooltip component and useMemo hooks, not stub implementations.

---

### Schema Deviation (Informational)

The 02-02-PLAN specified `SeasonalCalendarResponse.years_of_data` as the top-level field name. The implementation uses `total_years` instead. The frontend interface at `frontend/src/app/seasonal/page.tsx` line 45 matches this with `total_years: number`. The deviation is self-consistent across backend schema and frontend interface. The human verification confirmed the full stack works end-to-end, so this is an accepted deviation from the plan spec.

---

### Human Verification

Human verification was completed and approved before this automated verification. The following were confirmed visually:

1. **Chart renders correctly** — Monthly bar chart displays for Onion/Maharashtra with 12 bars.
2. **Best months coloured green** — Oct/Nov bars for Onion/Maharashtra show in green (#10b981).
3. **Worst month coloured red** — Bottom-price month shows in red (#ef4444).
4. **IQR error bars** — Asymmetric error bars visible on each bar (Q1-Q3 spread).
5. **Low-confidence warning banner** — Yellow/amber banner appears for thin-data selections.
6. **Coverage gap card** — Amber card with commodity/state names shown on 404.

---

### Commit Verification

All 5 commits from summaries confirmed present in git history:

| Commit | Description |
|--------|-------------|
| `45e5b7b` | feat(02-01): Alembic migration for seasonal_price_stats table |
| `0cdaf56` | feat(02-01): seasonal aggregator module with TDD unit tests |
| `3240b98` | feat(02-01): train_seasonal.py offline aggregation pipeline |
| `a54ed91` | feat(02-02): FastAPI seasonal schemas and endpoint |
| `27407ae` | feat(02-02): Next.js seasonal price calendar page |

---

## Gaps Summary

No gaps found. All must-haves from both plans are satisfied. All 6 requirements (SEAS-01 through SEAS-04, UI-01, UI-05) are implemented and verified. The full vertical slice — from parquet aggregation through FastAPI endpoint to Next.js Recharts chart — is wired and functionally complete. Human verification confirmed end-to-end UI behaviour.

---

_Verified: 2026-03-03T08:30:00Z_
_Verifier: Claude (gsd-verifier)_
