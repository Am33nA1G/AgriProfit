---
phase: 04-xgboost-forecasting-serving
plan: 06
subsystem: testing
tags: [playwright, e2e, react-query, route-mocking, chromium]

# Dependency graph
requires:
  - phase: 04-xgboost-forecasting-serving
    plan: 05
    provides: forecast page with commodity/state/district selectors, fallback banner, and Recharts chart

provides:
  - Playwright E2E test suite (3 tests) covering forecast page visual rendering, fallback banner, and cascading select reset
  - playwright.config.ts targeting http://localhost:3000
  - tests/e2e/forecast.spec.ts with route mocking for deterministic tests

affects:
  - phase 05 (and beyond) — any changes to forecast page DOM IDs must update these tests
  - CI pipeline integration (tests require running frontend + backend servers)

# Tech tracking
tech-stack:
  added: ["@playwright/test@1.58.2", "chromium-headless-shell v1208"]
  patterns:
    - Route mocking with page.route() for deterministic E2E tests without live ML models
    - Register specific route mocks before wildcard mocks (Playwright matches in registration order)
    - Wait for async React Query options to populate before selectOption (avoid DOM detachment)

key-files:
  created:
    - "frontend/playwright.config.ts"
    - "frontend/tests/e2e/forecast.spec.ts"
  modified:
    - "frontend/package.json"
    - "frontend/package-lock.json"

key-decisions:
  - "Wait for commodity options to populate before selectOption — React Query async fetch causes DOM detachment if selected too early"
  - "Register specific /commodities route mock before wildcard /forecast/** mock — Playwright route matching is first-match"
  - "No webServer block in playwright.config.ts — tests assume both servers already running (matches dev workflow)"
  - "route.continue() guard in wildcard handler for /commodities — defensive fallback even though specific route takes precedence"

patterns-established:
  - "gotoForecastPage helper: waitForSelector with non-empty option value before interacting with async-populated selects"
  - "Dual-route pattern: specific mock first, wildcard with url.includes guard second"

requirements-completed:
  - UI-02
  - UI-05

# Metrics
duration: 6min
completed: 2026-03-08
---

# Phase 4 Plan 06: Playwright E2E Tests for Forecast Page Summary

**3 Playwright E2E tests using route mocking automate the 3 VERIFICATION.md human-verification gaps: chart/badge rendering, fallback banner, and cascading select reset**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-08T17:19:39Z
- **Completed:** 2026-03-08T17:26:00Z
- **Tasks:** 3
- **Files modified:** 4 (playwright.config.ts, forecast.spec.ts, package.json, package-lock.json)

## Accomplishments
- Installed Playwright 1.58.2 with Chromium headless shell into frontend project
- Created `playwright.config.ts` targeting http://localhost:3000 with no auto-webServer (manual server workflow)
- Wrote 3 E2E tests that mock API responses deterministically via `page.route()`, eliminating need for live ML models
- All 3 tests pass in 6.2 seconds total against the running dev server

## Task Commits

Each task was committed atomically:

1. **Task 1: Install Playwright and write playwright.config.ts** - `e3bfd986` (chore)
2. **Task 2: Write E2E tests for the 3 VERIFICATION.md gaps** - `f08bd07c` (test)
3. **Task 2 fix: Fix commodity select timing in E2E tests** - `7684ece4` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `frontend/playwright.config.ts` - Playwright config: baseURL=localhost:3000, headless, list reporter, no webServer block
- `frontend/tests/e2e/forecast.spec.ts` - 3 E2E tests covering Gap 1 (chart+badges), Gap 2 (fallback banner), Gap 3 (cascading reset)
- `frontend/package.json` - Added @playwright/test@1.58.2 to devDependencies
- `frontend/package-lock.json` - Updated lock file

## Decisions Made
- No `webServer` block in playwright.config.ts — tests assume both frontend (port 3000) and backend (port 8000) are already running. This matches the real-world dev workflow described in VERIFICATION.md.
- Route mocking over live API calls — makes tests deterministic and independent of ML artifact availability. The forecast page uses useQuery with enabled guard and API route, so intercepting at the network layer tests the full React rendering path.
- Specific commodity route registered before wildcard to ensure correct mock resolution in Playwright's first-match route system.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed DOM detachment timing issue in commodity select interaction**
- **Found during:** Task 3 (running E2E tests)
- **Issue:** `page.selectOption('#commodity-select', value)` was called immediately after `waitForSelector('#commodity-select', visible)`. However, React Query fetches the commodity list asynchronously — when the response arrives, React re-renders and recreates the `<option>` elements, detaching the old DOM. Playwright times out waiting for the element to stabilize.
- **Fix:** Updated `gotoForecastPage()` to additionally wait for `#commodity-select option[value]:not([value=""])` to be attached before returning. This ensures at least one commodity option is rendered before any `selectOption()` call. Also added `route.continue()` guard inside the wildcard handler for `/commodities` URLs as defensive fallback.
- **Files modified:** frontend/tests/e2e/forecast.spec.ts
- **Verification:** All 3 tests passed in 6.2 seconds after fix
- **Committed in:** `7684ece4` (separate fix commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: DOM detachment race condition)
**Impact on plan:** Fix was necessary for correctness. No scope creep — still exactly 3 tests covering the 3 VERIFICATION.md gaps.

## Issues Encountered
- Playwright route matching requires specific mocks registered before wildcard mocks — documented in PLAN.md but the wildcard also matched `/commodities` unless explicitly guarded with `route.continue()`.
- The `gotoForecastPage` helper in the original plan waited for `#commodity-select` to be visible but not for its options to populate — this race condition caused DOM detachment errors on all 3 tests.

## User Setup Required
None - no external service configuration required. Tests run with `npx playwright test tests/e2e/forecast.spec.ts` from the `frontend/` directory (requires frontend on :3000 and backend on :8000 running).

## Next Phase Readiness
- Phase 4 verification gaps (UI-02, UI-05) are now automated — VERIFICATION.md can be updated from `human_needed` to `verified`
- Tests can be run in CI by starting both servers before the test step
- No ML artifacts required — route mocking makes tests fully self-contained

---
*Phase: 04-xgboost-forecasting-serving*
*Completed: 2026-03-08*
