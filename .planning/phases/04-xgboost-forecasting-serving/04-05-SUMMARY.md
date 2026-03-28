---
phase: 04-xgboost-forecasting-serving
plan: 05
subsystem: ui
tags: [nextjs, recharts, tanstack-query, forecast, xgboost]

# Dependency graph
requires:
  - phase: 04-xgboost-forecasting-serving
    provides: FastAPI /forecast/{commodity}/{district} endpoint with ForecastResponse schema

provides:
  - Next.js /forecast page with commodity/state/district selectors and 7/14-day horizon toggle
  - ForecastChart component: Recharts ComposedChart with confidence band (Area) and mid-line (Line)
  - forecastService.getForecast() typed API client
  - Skeleton loading.tsx for no-layout-shift loading experience
  - Fallback banner when tier_label === 'seasonal average fallback' (UI-05)

affects:
  - Phase 05 (soil advisor — farm advisory stack now has forecast + soil UI)
  - Phase 06 (arbitrage — sibling feature on same frontend)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Recharts ComposedChart stacked Area band (base Area transparent + bandRange fill) for confidence intervals
    - Cascading select reset: state change clears district, query only fires when commodity + district both selected
    - Confidence colour map (Green/Yellow/Red) drives chart fill and stroke colours

key-files:
  created:
    - frontend/src/services/forecast.ts
    - frontend/src/components/ForecastChart.tsx
    - frontend/src/app/forecast/page.tsx
    - frontend/src/app/forecast/loading.tsx
  modified: []

key-decisions:
  - "Fallback banner condition uses tier_label === 'seasonal average fallback' not coverage_message — explicit check matches plan spec and UI-05 requirement"
  - "ForecastChart uses stacked Area (bandRange = price_high - price_low) to render confidence interval band without custom shapes"
  - "coverage_message uses null-coalescing fallback text: ?? 'Insufficient price history. Showing seasonal averages.'"

patterns-established:
  - "ForecastChart: Recharts Area stackId='band' for rendering low-high confidence bands without custom SVG"
  - "Forecast page: useQuery enabled guard — !!commodity && !!district prevents API calls with empty params"

requirements-completed: [UI-02, UI-05]

# Metrics
duration: 8min
completed: 2026-03-03
---

# Phase 4 Plan 05: Price Forecast Frontend Summary

**XGBoost forecast page with Recharts confidence band chart, direction/confidence badges, and visible fallback banner for low-coverage districts**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-03T07:55:00Z
- **Completed:** 2026-03-03T08:03:52Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Forecast page at /forecast with commodity, state, district, and horizon selectors — cascading state reset on state change
- ForecastChart component with Recharts ComposedChart: stacked Area confidence band (low base + bandRange fill) and dashed mid-line
- Fallback banner (UI-05) shown when `tier_label === "seasonal average fallback"` with coverage_message and null-coalescing default text
- Direction badges (Rising/Falling/Stable) and confidence badges (High/Moderate/Low) with colour coding
- Skeleton loading.tsx with animate-pulse placeholder, no layout shift
- Data freshness note displayed always with `last_data_date`

## Task Commits

Each task was committed atomically:

1. **Task 1: Forecast API service and ForecastChart component** - `e4ef55f` (feat)
2. **Task 2: Forecast page with selectors, badges, and fallback banner** - `b5a80b3` (feat)

**Plan metadata:** `d6bb72e` (docs: complete plan)

## Files Created/Modified

- `frontend/src/services/forecast.ts` - forecastService.getForecast() with URL-encoded params and ForecastResponse/ForecastPoint interfaces
- `frontend/src/components/ForecastChart.tsx` - Recharts ComposedChart with confidence band using stacked Areas and colour map
- `frontend/src/app/forecast/page.tsx` - Full forecast UI: selectors, badges, fallback banner, chart, price range card, data freshness note
- `frontend/src/app/forecast/loading.tsx` - Skeleton loading placeholder with animate-pulse

## Decisions Made

- Fallback banner condition uses `tier_label === "seasonal average fallback"` (not `coverage_message &&`) — explicit check matches plan spec and UI-05 requirement precisely
- ForecastChart uses stacked Area approach (`stackId="band"`, transparent base + bandRange fill) to render confidence interval without custom SVG shapes
- `coverage_message` uses null-coalescing fallback: `?? "Insufficient price history. Showing seasonal averages."` — handles case where tier is fallback but message is null

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fallback banner condition updated to match plan spec**
- **Found during:** Task 2 review
- **Issue:** Initial implementation used `forecast.coverage_message &&` for the banner condition, but plan spec says "When tier_label is 'seasonal average fallback'" — these are semantically equivalent in practice but the plan's explicit condition is cleaner and matches UI-05 requirement
- **Fix:** Changed condition to `forecast.tier_label === "seasonal average fallback"` and added null-coalescing fallback text
- **Files modified:** frontend/src/app/forecast/page.tsx
- **Verification:** TypeScript compiles without errors
- **Committed in:** b5a80b3 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 correctness/spec alignment)
**Impact on plan:** Minor spec alignment. No scope creep.

## Issues Encountered

None - all files were pre-created before plan execution began. TypeScript compilation confirmed no errors in forecast files. Pre-existing TS errors in unrelated test files are out of scope.

## User Setup Required

None - no external service configuration required. The /forecast page connects to the existing backend forecast endpoint via the standard API client.

## Next Phase Readiness

- Forecast page complete, accessible at /forecast
- All 4 Phase 04 backend + frontend deliverables complete (ML schemas, training, serving core, API, frontend)
- Phase 04 is now fully complete — Phase 05 (soil advisor) and Phase 06 (arbitrage dashboard) can proceed independently

---
*Phase: 04-xgboost-forecasting-serving*
*Completed: 2026-03-03*
