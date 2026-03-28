---
phase: 05-soil-crop-advisor
plan: "02"
subsystem: soil-advisor-api-and-ui
tags: [fastapi, pydantic, sqlalchemy, nextjs, react-query, vitest, soil-advisor, tdd]

requires:
  - phase: 05-01
    provides: "soil_profiles and soil_crop_suitability tables, rank_crops(), generate_fertiliser_advice(), COVERED_STATES"

provides:
  - "GET /api/v1/soil-advisor/states — returns 21 covered state names"
  - "GET /api/v1/soil-advisor/districts?state= — distinct districts for a state"
  - "GET /api/v1/soil-advisor/blocks?state=&district= — distinct blocks for a district"
  - "GET /api/v1/soil-advisor/profile?state=&district=&block= — SoilAdvisorResponse with disclaimer, nutrient bars, crop rankings, fertiliser advice"
  - "backend/app/soil_advisor/schemas.py — SoilAdvisorResponse, NutrientDistribution, CropRecommendation, FertiliserAdvice"
  - "backend/app/soil_advisor/service.py — orchestrator: get_states, get_districts_for_state, get_blocks_for_district, get_block_profile, get_soil_advice"
  - "backend/app/soil_advisor/routes.py — FastAPI router with 4 GET endpoints"
  - "frontend/src/services/soil-advisor.ts — typed API client"
  - "frontend/src/app/soil-advisor/page.tsx — drill-down UI with disclaimer, CSS nutrient bars, crop list, fertiliser cards, coverage gap banner"
  - "backend/tests/test_soil_advisor_api.py — 21 integration tests via TestClient"
  - "frontend/src/app/soil-advisor/__tests__/soil-advisor.test.tsx — 3 Vitest behavioral tests"

affects:
  - Phase 06 (Mandi Arbitrage Dashboard — independent, no dependency)

tech-stack:
  added: []
  patterns:
    - "Query params (not path params) for state/district/block — avoids routing issues with hyphens and spaces in block names"
    - "Sync FastAPI handlers (def not async) for DB routes — matches project convention"
    - "Coverage check only on /profile endpoint — list endpoints work for any state"
    - "Optional seasonal_demand via OperationalError catch — Phase 2 table may not exist, never raises"
    - "CSS width-% nutrient bars instead of Recharts — simpler, mobile-friendly, DOM-testable"
    - "Non-dismissable SoilDisclaimer component — mandatory, always renders above crop list, no close button"
    - "vi.hoisted() stable router reference — prevents infinite render loop in tests with useEffect([router])"

key-files:
  created:
    - backend/app/soil_advisor/schemas.py
    - backend/app/soil_advisor/service.py
    - backend/app/soil_advisor/routes.py
    - backend/tests/test_soil_advisor_api.py
    - frontend/src/services/soil-advisor.ts
    - frontend/src/app/soil-advisor/page.tsx
    - frontend/src/app/soil-advisor/__tests__/soil-advisor.test.tsx
  modified:
    - backend/app/main.py

key-decisions:
  - "Query parameters used for state/district/block on /profile endpoint — block names like 'ANANTAPUR - 4689' contain hyphens and spaces, path segments would require URL encoding and create routing ambiguity"
  - "Coverage gate (COVERED_STATES check) applied only to /profile, not /districts or /blocks — list endpoints return empty arrays for unrecognised states rather than 404"
  - "Seasonal demand enrichment wrapped in broad exception catch — seasonal_price_stats table is a Phase 2 dependency that may not be present, feature degrades gracefully to None"
  - "CSS percentage-width divs for nutrient bars instead of Recharts — simpler DOM structure, easier to test, mobile-friendly, no charting library overhead"
  - "SoilDisclaimer has no toggle/dismiss/conditional — non-negotiable per plan spec; renders whenever results render"
  - "rank_crops() aggregates scores by crop_name before ranking — soil_crop_suitability has one row per (crop_name, nutrient), causing duplicate crop entries without aggregation (Rule 1 bug fix)"

patterns-established:
  - "Pattern 1: Soil advisor service uses SELECT MAX(cycle) subquery to select most recent data without requiring sorted pagination"
  - "Pattern 2: Local SQLite fixture pattern for integration tests (do not modify conftest.py; create local engine + SessionLocal + client fixture override)"

requirements-completed: [SOIL-01, SOIL-02, SOIL-03, SOIL-04, SOIL-05, UI-03, UI-05]

duration: 11min
completed: "2026-03-03"
---

# Phase 05 Plan 02: Soil Advisor API and UI Summary

**4 FastAPI soil-advisor endpoints (states/districts/blocks/profile) with ICAR suitability integration, 21 backend integration tests, and a Next.js drill-down UI with non-dismissable disclaimer, CSS nutrient bars, crop rankings, fertiliser advice cards, and coverage gap banner — human verification approved.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-03T01:12:08Z
- **Completed:** 2026-03-03T01:23:08Z
- **Tasks:** 3 of 3 (including checkpoint:human-verify — APPROVED)
- **Files modified:** 8 (7 created, 1 modified)

## Accomplishments
- 4 REST endpoints wired: /states (21 items), /districts, /blocks, /profile — all returning correct data from SQLite in-memory test DB
- 21 backend integration tests pass: profile response shape, disclaimer content, 5 nutrient distributions, crop rankings, fertiliser advice for N-deficient blocks, 404 with coverage_gap=true for PUNJAB
- 3 Vitest behavioral tests pass: disclaimer renders without dismiss button, district select disabled before state selected, coverage gap banner on 404
- SoilAdvisorResponse builds correctly from rank_crops() + generate_fertiliser_advice() from Plan 05-01
- Next.js page delivers chained selects, mandatory disclaimer, CSS nutrient bars, seasonal demand badges, fertiliser advice cards

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI schemas, service, routes, and integration tests** — `d06147b` (feat)
2. **Task 2: Next.js soil advisor page, API service layer, and Vitest behavioral tests** — `705f1ef` (feat)
3. **Fix: rank_crops duplicate crop_name aggregation (post-checkpoint)** — `7059a60` (fix)

**Plan metadata:** `6ecf70f` (docs: complete soil advisor API and UI plan)

## Files Created/Modified
- `backend/app/soil_advisor/schemas.py` — NutrientDistribution, CropRecommendation, FertiliserAdvice, SoilAdvisorResponse Pydantic models
- `backend/app/soil_advisor/service.py` — get_states, get_districts_for_state, get_blocks_for_district, get_block_profile, get_soil_advice, _get_seasonal_demand
- `backend/app/soil_advisor/routes.py` — APIRouter with 4 GET endpoints using Query params
- `backend/app/main.py` — soil_advisor_router import + include_router + Soil Advisor tag added to TAGS_METADATA
- `backend/tests/test_soil_advisor_api.py` — 21 integration tests via local SQLite TestClient fixture
- `frontend/src/services/soil-advisor.ts` — TypeScript interfaces + soilAdvisorApi object
- `frontend/src/app/soil-advisor/page.tsx` — React page with drill-down UI, SoilDisclaimer, NutrientBar, CropRow, FertiliserCard, CoverageGapBanner
- `frontend/src/app/soil-advisor/__tests__/soil-advisor.test.tsx` — 3 Vitest behavioral tests

## Decisions Made
- Query parameters for state/district/block on /profile to avoid URL encoding issues with block names containing hyphens and spaces (e.g., "ANANTAPUR - 4689")
- CSS percentage-width divs for nutrient distribution bars instead of Recharts (per plan spec)
- SoilDisclaimer renders with no dismiss/close/toggle — mandatory non-dismissable disclaimer
- seasonal_demand wrapped in broad exception catch — seasonal_price_stats table is optional Phase 2 dependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] rank_crops() produced duplicate crop_name entries**
- **Found during:** Task 3 (checkpoint:human-verify) — user reported duplicate React keys in crop recommendation list
- **Issue:** soil_crop_suitability has one row per (crop_name, nutrient). rank_crops() was iterating over raw DB rows and appending one ranked entry per row, causing each crop to appear N times (once per nutrient row). React raised duplicate key warnings; the UI showed 3-5 copies of each crop.
- **Fix:** Rewrote rank_crops() in `backend/app/soil_advisor/suitability.py` to accumulate scores into a `defaultdict(float)` keyed by crop_name, then build the ranked list from the aggregated totals — one entry per unique crop.
- **Files modified:** `backend/app/soil_advisor/suitability.py`
- **Verification:** All 21 backend integration tests pass; profile endpoint returns each crop exactly once with correct suitability_rank values.
- **Committed in:** `7059a60` (post-checkpoint fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential correctness fix. Without it, React rendered duplicate crop rows and raised duplicate key warnings. No scope creep.

## Issues Encountered

Human-verify checkpoint revealed the rank_crops() aggregation bug (duplicate crop entries per nutrient row). Fixed immediately post-approval and verified with full test suite.

## User Setup Required
Before the /profile endpoint returns live data, two steps are required:
1. Apply the migration: `cd backend && alembic upgrade e1f2a3b4c5d6`
2. Seed soil data: `cd backend && python scripts/seed_soil_suitability.py`

Integration tests use an in-memory SQLite fixture and pass without these steps.

## Next Phase Readiness
- Phase 05 Plan 02 is fully complete (human verification approved).
- Phase 05 is complete — both plans delivered and verified.
- Phase 06 (Mandi Arbitrage Dashboard) is independent and can proceed in parallel.
- The query-param endpoint pattern established here applies directly to Phase 6's arbitrage routes.
- The /soil-advisor page is production-ready once the migration and seeder are applied to the production DB.

## Self-Check: PASSED

### Files Exist
All 7 created files confirmed present on disk:
- FOUND: backend/app/soil_advisor/schemas.py
- FOUND: backend/app/soil_advisor/service.py
- FOUND: backend/app/soil_advisor/routes.py
- FOUND: backend/tests/test_soil_advisor_api.py
- FOUND: frontend/src/services/soil-advisor.ts
- FOUND: frontend/src/app/soil-advisor/page.tsx
- FOUND: frontend/src/app/soil-advisor/__tests__/soil-advisor.test.tsx
- FOUND: .planning/phases/05-soil-crop-advisor/05-02-SUMMARY.md

### Commits Verified

| Hash | Message |
|------|---------|
| d06147b | feat(05-02): FastAPI soil advisor schemas, service, routes, and integration tests |
| 705f1ef | feat(05-02): Next.js soil advisor page, API service layer, and Vitest behavioral tests |
| 7059a60 | fix(05-02): aggregate rank_crops by crop_name to eliminate duplicate React keys |
| 6ecf70f | docs(05-02): complete soil advisor API and UI plan — awaiting checkpoint |

---
*Phase: 05-soil-crop-advisor*
*Completed: 2026-03-03*
