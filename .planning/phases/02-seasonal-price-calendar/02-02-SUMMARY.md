---
phase: 02-seasonal-price-calendar
plan: "02"
subsystem: api, ui
tags: [fastapi, pydantic, nextjs, recharts, postgresql, tanstack-query]

# Dependency graph
requires:
  - phase: 02-01-seasonal-price-calendar
    provides: seasonal_price_stats table populated by train_seasonal.py

provides:
  - GET /api/v1/seasonal endpoint reading only from seasonal_price_stats
  - MonthlyStatPoint and SeasonalCalendarResponse Pydantic schemas
  - GET /api/v1/seasonal/commodities and /api/v1/seasonal/states list endpoints
  - Next.js /seasonal page with Recharts ComposedChart + IQR ErrorBar
  - Per-bar Cell colouring (green best, red worst, gray neutral)
  - Low-confidence yellow warning banner when years_of_data < 3
  - Coverage gap message on 404 for missing commodity/state combinations

affects:
  - phase: 04-xgboost-forecasting
  - phase: 02-seasonal-price-calendar

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FastAPI sync def endpoint (not async) with SQLAlchemy Session for DB-heavy work
    - Query params for commodity/state names instead of path params (avoids URL-encoding issues with spaces)
    - Recharts ComposedChart + Bar + ErrorBar for asymmetric IQR visualisation
    - TanStack Query useQuery with enabled guard (both commodity and state non-empty before fetch)
    - Searchable commodity dropdown backed by /seasonal/commodities list endpoint (avoids managing 314-item static list on frontend)

key-files:
  created:
    - backend/app/seasonal/__init__.py
    - backend/app/seasonal/schemas.py
    - backend/app/seasonal/routes.py
    - frontend/src/app/seasonal/page.tsx
  modified:
    - backend/app/main.py

key-decisions:
  - "Existing partial code from prior session reused: routes.py, schemas.py, and page.tsx all verified complete and correct — no rewrite needed"
  - "GET /api/v1/seasonal reads only seasonal_price_stats (never price_history) — query params used for commodity+state to avoid URL-encoding issues with state names containing spaces"
  - "train_seasonal.py must be run offline to populate seasonal_price_stats before the endpoint returns data; endpoint returns 404 (not 500) for unseeded commodity+state pairs"
  - "is_best/is_worst only set when years_of_data >= 3 — sparse data series never receive best/worst labels to avoid misleading farmers"
  - "Recharts ComposedChart with Bar + ErrorBar for IQR visualisation; asymmetric error bars computed as [median-q1, q3-median]"
  - "Bonus /seasonal/commodities and /seasonal/states list endpoints added to drive frontend dropdowns from DB (avoids maintaining 314-item static array in frontend)"
  - "Case-insensitive matching added to commodity and state queries via ILIKE — handles variant capitalisation from user input"

patterns-established:
  - "Seasonal API pattern: aggregate offline, serve from stats table, never scan price_history at request time"
  - "IQR error bar pattern: errorY=[median-q1, q3-median] as asymmetric tuple for Recharts ErrorBar dataKey"
  - "Low-confidence UX: yellow warning banner above chart, not a blocked/hidden chart — users see data with caveat"
  - "Coverage gap UX: styled gray card with commodity+state names when 404 — never an unhandled error boundary"

requirements-completed: [SEAS-01, SEAS-02, SEAS-03, UI-01, UI-05]

# Metrics
duration: 15min
completed: "2026-03-03"
---

# Phase 2 Plan 02: Seasonal Price Calendar - API + UI Summary

**FastAPI GET /api/v1/seasonal endpoint + Recharts monthly bar chart at /seasonal, serving pre-aggregated median/IQR stats for 314 commodities with green/red best-worst month colouring and low-confidence warning**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-03T07:23:00Z
- **Completed:** 2026-03-03T07:38:00Z
- **Tasks:** 2 code tasks + 1 human verification checkpoint
- **Files modified:** 5

## Accomplishments

- FastAPI seasonal endpoint reads only `seasonal_price_stats` (zero price_history scans), returns 12-month MonthlyStatPoint array with median, Q1, Q3, IQR, is_best, is_worst, month_rank, and top-level low_confidence flag
- Next.js page at /seasonal with Recharts ComposedChart: per-bar Cell colouring (green for best months, red for worst, gray neutral), asymmetric IQR ErrorBar, custom tooltip, best/worst month summary cards, yellow low-confidence banner, and gray coverage-gap card on 404
- Bonus list endpoints /seasonal/commodities and /seasonal/states drive the frontend dropdowns from DB — no 314-item static array needed on the frontend
- Human verification passed: chart renders correctly with best/worst month colouring confirmed

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI seasonal schemas + endpoint** - `a54ed91` (feat)
2. **Task 2: Next.js seasonal calendar page** - `27407ae` (feat)

## Files Created/Modified

- `backend/app/seasonal/__init__.py` - Empty package init
- `backend/app/seasonal/schemas.py` - MonthlyStatPoint and SeasonalCalendarResponse Pydantic models with ConfigDict(from_attributes=True)
- `backend/app/seasonal/routes.py` - GET /seasonal endpoint + bonus /seasonal/commodities and /seasonal/states list endpoints; reads only seasonal_price_stats; ILIKE for case-insensitive matching; 404 on unknown pair
- `backend/app/main.py` - seasonal_router registered at /api/v1; Seasonal tag metadata added
- `frontend/src/app/seasonal/page.tsx` - 458-line "use client" page: searchable commodity dropdown, state selector, ComposedChart with Bar+ErrorBar, Cell colouring, low-confidence banner, coverage-gap card, loading/error states, custom tooltip

## Decisions Made

- **Existing code reused without rewrite:** Prior session had already implemented routes.py, schemas.py, and page.tsx. Verified complete and correct against plan spec — no reimplementation needed.
- **Query params over path params:** `?commodity=X&state=Y` used instead of `/seasonal/{commodity}/{state}` to avoid URL-encoding issues with state names containing spaces (e.g. "West Bengal", "Andhra Pradesh").
- **train_seasonal.py offline prerequisite:** The endpoint returns 404 (not 500/503) for unseeded combinations — this is correct behaviour; developers must populate seasonal_price_stats by running train_seasonal.py against the parquet before the endpoint returns data.
- **is_best/is_worst guarded by years_of_data >= 3:** Sparse series (< 3 years) never receive best/worst labels; the low_confidence flag signals this to the frontend.
- **Bonus list endpoints:** /seasonal/commodities and /seasonal/states were added to serve frontend dropdowns from live DB, avoiding a 314-item static array in the frontend that could go stale.
- **Case-insensitive ILIKE matching:** Commodity and state queries use ILIKE to handle variant capitalisation from user input without requiring exact-match normalisation on the frontend.

## Deviations from Plan

None - plan executed exactly as written. Prior session had pre-built the implementation; this plan session verified correctness and obtained human approval.

## Issues Encountered

None. All code was verified correct against plan spec before the human verification checkpoint. Human approved without requesting any changes.

## User Setup Required

**train_seasonal.py must be run before the /seasonal endpoint can return data.**

The seasonal_price_stats table is empty until populated. To populate it:

```bash
cd backend
python scripts/train_seasonal.py
```

Prerequisites: Live PostgreSQL with price_bounds populated, and the 25M-row `agmarknet_daily_10yr.parquet` file at the repo root. See `02-01-SUMMARY.md` for full setup details.

## Next Phase Readiness

- Phase 2 is now complete: both plans (02-01 aggregation pipeline, 02-02 API + UI) are done
- Seasonal calendar provides the "seasonal average fallback" that Phase 4 (XGBoost Forecasting) will use for commodity-district pairs below the 730-day training threshold
- Phase 4 (04-01 through 04-05) is unblocked — depends on Phase 3 (complete) and Phase 1 (complete)

---
*Phase: 02-seasonal-price-calendar*
*Completed: 2026-03-03*
