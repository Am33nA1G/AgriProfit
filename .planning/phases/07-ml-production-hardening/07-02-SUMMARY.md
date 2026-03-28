---
phase: 07-ml-production-hardening
plan: 02
subsystem: frontend-testing
tags: [tdd, vitest, red-state, forecast, testing]
dependency_graph:
  requires: []
  provides: [forecast-page-test-stubs]
  affects: [frontend/src/app/forecast/page.tsx]
tech_stack:
  added: []
  patterns: [vitest-stable-router, queryClient-wrapper, forecastService-mock]
key_files:
  created:
    - frontend/src/app/forecast/__tests__/page.test.tsx
  modified: []
decisions:
  - "Stable lucide-react mock uses explicit named exports (not Proxy) — matches established pattern from MEMORY.md"
  - "Router mock in test file overrides setup.ts global — forecast page does not use useRouter so global would suffice, but explicit override documents intent"
  - "Test uses document.getElementById() for selects (id-based) rather than role queries — forecast page does not attach aria-label to selects"
  - "forecastService mock returns minimal objects with (as any) cast for Phase 7 fields not yet in the TypeScript interface"
metrics:
  duration_seconds: 123
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
  completed_date: "2026-03-09"
---

# Phase 7 Plan 02: Forecast Page Test Stubs (RED) Summary

**One-liner:** Failing Vitest test stubs for PROD-02 (chart hidden on Red confidence), PROD-03 (Uncertain direction badge), and PROD-05 (stale data banner) — all 3 assert UI behaviors not yet implemented in page.tsx.

## What Was Built

Created `frontend/src/app/forecast/__tests__/page.test.tsx` with 3 failing test cases covering the Phase 7 frontend requirements. Tests mock `forecastService.getForecast` with controlled responses containing the new Phase 7 fields (`is_stale`, `data_freshness_days`, `n_markets`, `typical_error_inr`), trigger the forecast query by selecting commodity + state + district via fireEvent, then assert UI behaviors that don't exist yet.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create failing Vitest test file for page.tsx Phase 7 behaviors | 1372c7e8 | frontend/src/app/forecast/__tests__/page.test.tsx |

## RED State Confirmed

All 3 tests fail with assertion errors (not import/syntax errors):

- **stale_banner_renders_when_is_stale**: `Unable to find an element by: [data-testid="stale-data-banner"]` — element does not exist in page.tsx yet
- **chart_hidden_when_confidence_red**: `expected document not to contain element, found <div data-testid="forecast-chart">` — no Red confidence gate in chart render block
- **uncertain_badge_renders**: `Unable to find text 'Uncertain'` — `DIRECTION_CONFIG` has no `uncertain` key

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: `frontend/src/app/forecast/__tests__/page.test.tsx`
- FOUND: commit `1372c7e8`
