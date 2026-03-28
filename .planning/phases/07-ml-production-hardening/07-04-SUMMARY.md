---
phase: 07-ml-production-hardening
plan: 04
subsystem: ui
tags: [typescript, react, next.js, vitest, forecast, trust-signals]

# Dependency graph
requires:
  - phase: 07-ml-production-hardening
    provides: Backend PROD fixes — is_stale, n_markets, typical_error_inr, direction=uncertain, confidence_colour=Red fields in API response

provides:
  - ForecastResponse TypeScript interface extended with 4 new fields and uncertain direction union
  - Stale data banner (yellow, id+data-testid=stale-data-banner) above chart when is_stale=true
  - Chart suppressed entirely when confidence_colour=Red
  - UNCERTAIN direction badge in neutral grey
  - CONFIDENCE_CONFIG labels updated: Green=Reliable, Yellow=Directional only
  - Farmer metadata footer showing n_markets and typical_error_inr below chart

affects:
  - Any Phase 7 continuation plan referencing forecast page UI
  - E2E tests that rely on confidence badge labels

# Tech tracking
tech-stack:
  added: []
  patterns:
    - data-testid on trust-signal elements for test selectability alongside id attribute
    - Confidence gate in chart render condition (short-circuit && chain)

key-files:
  created: []
  modified:
    - frontend/src/services/forecast.ts
    - frontend/src/app/forecast/page.tsx
    - frontend/src/app/forecast/__tests__/page.test.tsx

key-decisions:
  - "data-testid added alongside id on stale-data-banner div — test uses getByTestId while plan spec uses id; both attributes present for compatibility"
  - "Test wait condition updated from 'Moderate Confidence' to 'Directional only' to match new Yellow label — test was the ground truth stub but its intermediate wait needed to match the implementation label"

patterns-established:
  - "Trust signal elements carry both id (for CSS/E2E selection) and data-testid (for Vitest getByTestId) attributes"

requirements-completed:
  - PROD-02
  - PROD-03
  - PROD-05

# Metrics
duration: 15min
completed: 2026-03-09
---

# Phase 7 Plan 04: Frontend Trust Signals Summary

**TypeScript ForecastResponse extended with 4 trust-signal fields; forecast page gains stale banner, UNCERTAIN badge, Red confidence chart gate, and farmer metadata footer — all 3 Vitest tests GREEN, human-verified**

## Performance

- **Duration:** ~15 min (including human checkpoint)
- **Started:** 2026-03-09T06:02:00Z
- **Completed:** 2026-03-09T06:17:00Z
- **Tasks:** 3 of 3 (complete)
- **Files modified:** 4

## Accomplishments
- Extended `ForecastResponse` TypeScript interface: direction union adds 'uncertain', 4 new fields (data_freshness_days, is_stale, n_markets, typical_error_inr)
- Forecast page renders stale data warning banner (yellow) above badges when is_stale=true
- Forecast chart is hidden entirely when confidence_colour='Red' (corrupted model protection)
- UNCERTAIN direction badge renders in neutral grey slate tones
- Confidence badge labels updated: Green="Reliable", Yellow="Directional only"
- Farmer metadata footer replaces old data freshness note, shows n_markets and typical_error_inr
- All 3 Phase 7 Wave 0 Vitest tests pass GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend TypeScript ForecastResponse interface** - `26d52d14` (feat)
2. **Task 2: Update page.tsx with trust signals** - `260cde53` (feat)
3. **Post-checkpoint fix: commodity dropdown loading state** - `2a99e72a` (fix)
4. **Task 3: Human checkpoint** — APPROVED (visual verification passed)

## Files Created/Modified
- `frontend/src/services/forecast.ts` — Added 'uncertain' to direction union; added 4 new interface fields
- `frontend/src/app/forecast/page.tsx` — DIRECTION_CONFIG uncertain entry, CONFIDENCE_CONFIG label updates, stale banner, chart Red gate, farmer footer, commodity dropdown loading state fix
- `frontend/src/app/forecast/__tests__/page.test.tsx` — Updated waitFor condition from 'Moderate Confidence' to 'Directional only' (deviation fix)

## Decisions Made
- Used `data-testid` alongside `id` on the stale banner div — the Wave 0 test stub uses `getByTestId`, while the plan spec defines `id`; both are present
- Updated test's intermediate waitFor condition from 'Moderate Confidence' to 'Directional only' so it matches the new label implementation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test wait condition to match new confidence label**
- **Found during:** Task 2 (page.tsx trust signals)
- **Issue:** Wave 0 test stub used `getByText('Moderate Confidence')` as a waitFor condition in the uncertain badge test. Plan mandates changing Yellow label to "Directional only". With the label change, the wait would timeout and the test would fail.
- **Fix:** Updated waitFor condition to `getByText('Directional only')` to match the new label. The final assertion (`getByText('Uncertain')`) remains unchanged.
- **Files modified:** frontend/src/app/forecast/__tests__/page.test.tsx
- **Verification:** All 3 Vitest tests pass GREEN
- **Committed in:** 260cde53 (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added data-testid alongside id on stale banner**
- **Found during:** Task 2 (page.tsx trust signals)
- **Issue:** Test uses `screen.getByTestId('stale-data-banner')` but plan spec only specifies `id="stale-data-banner"`. Without data-testid, the test would fail.
- **Fix:** Added both `id="stale-data-banner"` and `data-testid="stale-data-banner"` to the banner div.
- **Files modified:** frontend/src/app/forecast/page.tsx
- **Verification:** Test 1 (stale banner) passes GREEN
- **Committed in:** 260cde53 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 correctness, 1 missing attribute)
**Impact on plan:** Both fixes required for tests to pass. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- All frontend trust signals implemented, tested (Vitest GREEN), and human-verified
- Plan 07-04 fully complete — phase 7 can proceed to remaining plans

---
*Phase: 07-ml-production-hardening*
*Completed: 2026-03-09*
