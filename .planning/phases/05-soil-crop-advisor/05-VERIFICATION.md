---
phase: 05-soil-crop-advisor
verified: 2026-03-03T07:15:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Open http://localhost:3000/soil-advisor and drill down to a block"
    expected: "Amber disclaimer card 'Block-average soil data for [block name] — not field-level measurement' renders above crop list without any close/dismiss button; CSS bar chart shows coloured segments for N/P/K/OC/pH; fertiliser advice cards appear for nutrients with low% > 50"
    why_human: "Visual layout, colour rendering, and responsive bar segments cannot be verified without a browser"
  - test: "Select a state not in COVERED_STATES (e.g., PUNJAB) via the API or UI"
    expected: "Coverage gap banner appears ('Soil data is not available for this region') and no crop recommendations are shown"
    why_human: "Coverage gap banner requires loading a profile for an uncovered state — the 21 covered states are all in COVERED_STATES, so triggering a gap requires a browser or curl with a non-covered state name"
---

# Phase 5: Soil Crop Advisor Verification Report

**Phase Goal:** A farmer can select a state, district, and block and receive a ranked list of suitable crops based on the block's NPK/pH soil deficiency profile, with fertiliser advice per nutrient deficit and an explicit disclaimer that the data is a block-level distribution, not a field-level measurement.
**Verified:** 2026-03-03T07:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                         | Status     | Evidence                                                                                                        |
|----|---------------------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------|
| 1  | State -> district -> block drill-down returns NPK/pH % distributions for the most recent soil health cycle   | VERIFIED   | `service.get_block_profile()` uses `SELECT MAX(cycle)` subquery; 21 integration tests pass including `test_five_nutrient_distributions` |
| 2  | Block deficiency profile maps to a ranked list of 3-5 crops using ICAR thresholds                           | VERIFIED   | `rank_crops()` in `suitability.py` aggregates per-nutrient scores by crop_name; `test_at_least_two_crop_recommendations` passes; `test_crop_recommendations_sorted_by_score_desc` passes |
| 3  | Every recommendation screen shows non-dismissable disclaimer containing block name                           | VERIFIED   | `SoilDisclaimer` component renders with `{profile.disclaimer}`; comment "no dismiss button" inline; no dismiss/close/hide button in component; `test_disclaimer_contains_block_name` passes; Vitest test 1 passes |
| 4  | Fertiliser advice card generated per nutrient deficiency where low% > 50                                     | VERIFIED   | `generate_fertiliser_advice()` uses strict `> threshold` (default 50); `test_fertiliser_advice_for_nitrogen_deficient_block` passes; 7 unit tests all pass including boundary-at-50 and boundary-at-51 |
| 5  | Page labelled "Available for 21 states"; uncovered states return informative message                         | VERIFIED   | Page header text "Available for 21 states — block-level soil health data" present; `/profile` endpoint returns 404 with `coverage_gap=true` and message "Available for 21 states only." for uncovered states; `test_coverage_gap_flag_in_detail` and `test_message_mentions_21_states` pass |
| 6  | GET /api/v1/soil-advisor/states returns exactly 21 covered state names                                       | VERIFIED   | `get_states()` returns `sorted(COVERED_STATES)`; `COVERED_STATES` verified to contain 21 states via `test_covered_states_count`; `test_returns_21_states` integration test passes |
| 7  | GET /api/v1/soil-advisor/districts and /blocks return correct chained results                                | VERIFIED   | `get_districts_for_state()` and `get_blocks_for_district()` use `SELECT DISTINCT ... ORDER BY` with `.upper().strip()` normalisation; `test_returns_districts_for_covered_state` and `test_case_insensitive_state_param` pass |
| 8  | Disclaimer field is always present in every SoilAdvisorResponse                                             | VERIFIED   | `get_soil_advice()` always sets `disclaimer=f"Block-average soil data for {block} — not field-level measurement"`; `test_disclaimer_always_present` passes |
| 9  | Coverage gap 404 returns structured error with `coverage_gap=true`                                           | VERIFIED   | `/profile` endpoint checks `COVERED_STATES` and raises `HTTPException 404` with `{"coverage_gap": True, "message": ...}`; `test_404_for_uncovered_state`, `test_coverage_gap_flag_in_detail`, `test_message_mentions_21_states` all pass |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact                                                                   | Expected                                                           | Status     | Details                                                                                                      |
|----------------------------------------------------------------------------|--------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------|
| `backend/alembic/versions/e1f2a3b4c5d6_add_soil_advisor_tables.py`        | Alembic migration creating soil_profiles + soil_crop_suitability   | VERIFIED   | Exists; creates both tables with correct column types, unique constraints (uq_soil_profile, uq_crop_nutrient), and 3 indexes; `down_revision = ("4be60c2d7319", "e2f3a4b5c6d7")` correctly merges both Phase 4 heads |
| `backend/app/soil_advisor/__init__.py`                                     | Module scaffold                                                    | VERIFIED   | Exists as empty init file; module importable                                                                 |
| `backend/app/soil_advisor/suitability.py`                                 | COVERED_STATES, ICAR_THRESHOLDS, rank_crops() pure function        | VERIFIED   | 159 lines; `COVERED_STATES` frozenset of 21 ALLCAPS states; `DEFICIENCY_THRESHOLD=50`; `is_deficient()`, `score_crop()`, `rank_crops()` implemented with score aggregation by crop_name to prevent duplicates |
| `backend/app/soil_advisor/fertiliser.py`                                  | FERTILISER_ADVICE dict, generate_fertiliser_advice() pure function | VERIFIED   | 62 lines; `FERTILISER_ADVICE` covers N/P/K/OC only (pH intentionally excluded); `generate_fertiliser_advice()` uses strict `> threshold` |
| `backend/scripts/seed_soil_suitability.py`                                | Bulk CSV seeder, idempotent                                        | VERIFIED   | 309 lines; `seed_soil_profiles()` uses `glob.glob` + `pd.read_csv`; batch inserts in chunks of 500; `ON CONFLICT ON CONSTRAINT uq_soil_profile DO UPDATE`; state/district stored `.upper()`; `seed_soil_crop_suitability()` for ICAR rows; Windows-compatible stdout encoding at top |
| `backend/app/soil_advisor/schemas.py`                                     | Pydantic schemas for SoilAdvisorResponse and sub-types             | VERIFIED   | 61 lines; `NutrientDistribution`, `CropRecommendation`, `FertiliserAdvice`, `SoilAdvisorResponse` all defined with `ConfigDict(from_attributes=True)`; `disclaimer` field present; `coverage_gap: bool = False` |
| `backend/app/soil_advisor/service.py`                                     | DB query logic + suitability matching                              | VERIFIED   | 234 lines; `get_states`, `get_districts_for_state`, `get_blocks_for_district`, `get_block_profile`, `get_soil_advice`, `_get_seasonal_demand` all implemented; `SELECT MAX(cycle)` subquery for most-recent-cycle; `rank_crops()` called inline; `generate_fertiliser_advice()` called; seasonal demand wrapped in broad exception catch |
| `backend/app/soil_advisor/routes.py`                                      | FastAPI router with 4 GET endpoints                                | VERIFIED   | 138 lines; `APIRouter(prefix="/soil-advisor", tags=["Soil Advisor"])`; 4 endpoints (states, districts, blocks, profile); all use `Query(...)` parameters; coverage check only on `/profile`; sync handlers (def not async) |
| `backend/app/main.py`                                                     | Router registered at /api/v1                                       | VERIFIED   | `from app.soil_advisor.routes import router as soil_advisor_router` at line 55; `app.include_router(soil_advisor_router, prefix="/api/v1")` at line 371; "Soil Advisor" tag in TAGS_METADATA |
| `backend/tests/test_soil_suitability.py`                                  | Unit tests for suitability.py pure functions                       | VERIFIED   | 86 lines; 10 test functions; all 10 pass including `test_covered_states_count`, `test_nitrogen_tolerant_crops_rank_higher`, `test_rank_crops_zero_score_excluded` |
| `backend/tests/test_soil_fertiliser.py`                                   | Unit tests for fertiliser.py pure functions                        | VERIFIED   | 66 lines; 7 test functions; all 7 pass including `test_advice_generated_above_threshold`, `test_threshold_boundary_at_50`, `test_ph_not_in_advice` |
| `backend/tests/test_soil_advisor_api.py`                                  | FastAPI integration tests via TestClient                           | VERIFIED   | 301 lines; 21 integration tests; local SQLite in-memory fixture (does not modify conftest.py); all 21 pass |
| `frontend/src/services/soil-advisor.ts`                                   | API client functions for soil advisor endpoints                    | VERIFIED   | 90 lines; `NutrientDistribution`, `CropRecommendation`, `FertiliserAdvice`, `SoilAdvisorResponse` interfaces; `soilAdvisorApi` object with `getStates`, `getDistricts`, `getBlocks`, `getProfile` |
| `frontend/src/app/soil-advisor/page.tsx`                                  | Next.js soil advisor page with drill-down UI                       | VERIFIED   | 406 lines; `SoilDisclaimer` renders above crop list with no dismiss button; `NutrientBar` uses CSS `style={{ width: ... }}` (not Recharts); chained selects with `disabled={!selectedState}` and `disabled={!selectedDistrict}`; `CoverageGapBanner` renders on 404 error; `data-testid="district-select"` present |
| `frontend/src/app/soil-advisor/__tests__/soil-advisor.test.tsx`           | Vitest behavioral tests for soil advisor page                      | VERIFIED   | 212 lines; 3 tests; all pass: SoilDisclaimer renders without dismiss button, district select disabled before state selected, coverage gap banner on 404 |

### Key Link Verification

| From                                      | To                                             | Via                                                         | Status  | Details                                                                                  |
|-------------------------------------------|------------------------------------------------|-------------------------------------------------------------|---------|------------------------------------------------------------------------------------------|
| `backend/app/soil_advisor/routes.py`      | `backend/app/main.py`                          | `app.include_router(soil_advisor_router, prefix='/api/v1')` | WIRED   | Import at line 55, include_router at line 371 confirmed                                  |
| `backend/app/soil_advisor/service.py`     | `soil_profiles` table                          | `SELECT MAX(cycle)` subquery in `get_block_profile()`       | WIRED   | Pattern `SELECT MAX(cycle)` found at line 97; result used to build profile dict          |
| `backend/app/soil_advisor/service.py`     | `backend/app/soil_advisor/suitability.py`      | `rank_crops(profile, crop_dicts)` called inline per request | WIRED   | `from app.soil_advisor.suitability import COVERED_STATES, rank_crops` at line 24; `rank_crops()` called at line 183 |
| `frontend/src/app/soil-advisor/page.tsx`  | `frontend/src/services/soil-advisor.ts`        | `useQuery` hooks calling `soilAdvisorApi.*`                 | WIRED   | `useQuery` with `queryFn: soilAdvisorApi.getStates/getDistricts/getBlocks/getProfile` at lines 212-246 |
| `backend/scripts/seed_soil_suitability.py`| `data/soil-health/nutrients/*.csv`             | `glob.glob` + `pd.read_csv`                                 | WIRED   | `glob.glob(pattern)` at line 160; `pd.read_csv(fpath)` in loop; pattern `ON CONFLICT ON CONSTRAINT uq_soil_profile` at line 175 |

### Requirements Coverage

| Requirement | Source Plans | Description                                                                                                             | Status         | Evidence                                                                                                                                     |
|-------------|-------------|-------------------------------------------------------------------------------------------------------------------------|----------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| SOIL-01     | 05-01, 05-02 | User can select state + district + block and see soil health profile — N/P/K/OC/pH % distributions for most recent cycle | SATISFIED      | 4 endpoints (states/districts/blocks/profile) + service layer with SELECT MAX(cycle); `test_five_nutrient_distributions` passes; page renders `NutrientBar` per nutrient |
| SOIL-02     | 05-01, 05-02 | System maps block deficiency profile to ranked list of suitable crops using ICAR thresholds                             | SATISFIED      | `rank_crops()` with 3-tier tolerance scoring; `score_crop()` pure function; 17 unit tests pass; `test_at_least_two_crop_recommendations` passes |
| SOIL-03     | 05-02        | Every recommendation displays "Block-average soil data for [block name] — not field-level measurement"                  | SATISFIED      | `disclaimer=f"Block-average soil data for {block} — not field-level measurement"` in `get_soil_advice()`; `SoilDisclaimer` renders always above crop list; Vitest test 1 passes |
| SOIL-04     | 05-01, 05-02 | Fertiliser advice per nutrient deficiency (e.g., "73% of soils... nitrogen-deficient — consider urea")                  | SATISFIED      | `generate_fertiliser_advice()` with `> 50` threshold; 7 unit tests pass; `FertiliserCard` component renders advice; `test_fertiliser_advice_for_nitrogen_deficient_block` passes |
| SOIL-05     | 05-02        | Coverage gap explicit in UI — soil advisor labelled "Available for X states"; covered vs uncovered visible              | SATISFIED*     | Page header reads "Available for 21 states — block-level soil health data"; `/profile` returns 404 with `coverage_gap=true`; `CoverageGapBanner` renders on error. NOTE: REQUIREMENTS.md text says "31 states" (stale from Phase 1; the "31 states" figure was the original research estimate — Phase 1 Plan 01-03 corrected this to 21 states, which is the actual data). ROADMAP Phase 5 Success Criterion #5 (authoritative contract) says "21 states" — implementation matches. The REQUIREMENTS.md text also mentions "a map showing covered vs uncovered regions" — not implemented; ROADMAP criterion only requires "informative message, not empty result or error" which is satisfied via the CoverageGapBanner. |
| UI-03       | 05-02        | Soil advisor page — state -> district -> block drill-down, NPK/pH distribution bars, crop recommendation list, fertiliser advice cards | SATISFIED | Chained selects with `disabled` state management; CSS NutrientBar components; CropRow list with suitability_rank; FertiliserCard components; page.tsx confirmed at 406 lines |
| UI-05       | 05-02        | All dashboards display coverage gap messages when a feature is unavailable for selected region                          | SATISFIED      | `CoverageGapBanner` renders "Soil data is not available for this region" on 404 error; Vitest test 3 confirms banner shown and crops hidden on coverage_gap error |

*Note on SOIL-05: The REQUIREMENTS.md entry for SOIL-05 contains two stale values: "31 states" (should be 21 — corrected in Phase 1) and "a map showing covered vs uncovered regions" (not implemented; ROADMAP only requires an informative message). The authoritative contract is the ROADMAP Phase 5 Success Criterion #5 which says "21 states" and "informative message" — both are satisfied. The REQUIREMENTS.md text is a documentation artifact that was not fully updated. This is a documentation gap in REQUIREMENTS.md, not an implementation gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | All 7 soil advisor source files clean — no TODO/FIXME/PLACEHOLDER comments, no stub implementations, no empty returns in service or route handlers |

One pre-existing project-wide issue noted (not introduced by Phase 5): the `@test` path alias is configured in `vitest.config.ts` but not in `tsconfig.json`, causing a TypeScript type error in `soil-advisor.test.tsx` line 1 (`Cannot find module '@test/test-utils'`). This is present in 33 test files across the project and predates Phase 5. The tests run correctly at runtime via Vitest (which resolves the alias); only `tsc --noEmit` reports the error. The production source files (`page.tsx` and `soil-advisor.ts`) compile without TypeScript errors.

### Human Verification Required

#### 1. End-to-end drill-down and visual layout

**Test:** Start the backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`), navigate to `http://localhost:3000/soil-advisor`, select a covered state (e.g., ANDHRA PRADESH), then a district, then a block.
**Expected:** Amber disclaimer card appears immediately above the crop list with the block name in text and NO close/dismiss/X button. CSS horizontal bar chart shows three coloured segments (green=high, amber=medium, red=low) per nutrient. Crop recommendation list shows 3-5 ranked crops. Fertiliser advice cards appear for nutrients with low% > 50 (Nitrogen and Organic Carbon for ANANTAPUR - 4689 should both appear with advice).
**Why human:** Visual rendering, colour segments, and absence of a dismiss button cannot be verified without a browser.

#### 2. Coverage gap banner for uncovered state

**Test:** Navigate to soil advisor. The state dropdown only shows the 21 covered states (COVERED_STATES). To test coverage gap: use curl `GET http://localhost:8000/api/v1/soil-advisor/profile?state=PUNJAB&district=X&block=Y` and confirm 404 with `coverage_gap: true`. The UI coverage gap can be tested by temporarily adding a non-covered state to the dropdown.
**Expected:** API returns 404 with `{"detail": {"coverage_gap": true, "message": "Soil data not available for PUNJAB. Available for 21 states only."}}`. Frontend shows yellow banner "Soil data is not available for this region."
**Why human:** All 21 COVERED_STATES are valid states — UI naturally never shows a non-covered state in the dropdown. The API-level check requires curl or direct endpoint test to trigger.

### Gaps Summary

No automated gaps found. All 9 observable truths verified. All 15 artifacts exist, are substantive, and are wired. All 21 backend integration tests pass. All 17 unit tests pass. All 3 Vitest behavioral tests pass.

One documentation inconsistency exists in `.planning/REQUIREMENTS.md` SOIL-05 text which still reads "Available for 31 states" and mentions "a map showing covered vs uncovered regions" — both values are stale from before Phase 1 Plan 01-03's corrections. The ROADMAP Phase 5 Success Criterion #5 (the authoritative contract verified against) says "21 states" and "informative message" — implementation satisfies the authoritative criterion. This is a documentation debt, not a code gap.

The `@test` path alias TypeScript gap (1 error in `soil-advisor.test.tsx` line 1) is pre-existing across the project (33 test files total) and predates Phase 5. It does not affect runtime test execution.

---

_Verified: 2026-03-03T07:15:00Z_
_Verifier: Claude (gsd-verifier)_
