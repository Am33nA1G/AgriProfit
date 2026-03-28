---
phase: 7
slug: ml-production-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), Vitest (frontend) |
| **Config file** | `backend/pytest.ini`, `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && python -m pytest tests/test_forecast_service.py tests/test_forecast_api.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest -x -q && cd frontend && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_forecast_service.py tests/test_forecast_api.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest -x -q && cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | PROD-01 | unit | `pytest tests/test_forecast_service.py::test_corrupted_model_blocked -x` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 0 | PROD-02 | unit | `pytest tests/test_forecast_service.py::test_confidence_colour_mapping -x` | ✅ exists (line 111) | ⬜ pending |
| 7-01-03 | 01 | 0 | PROD-03 | unit | `pytest tests/test_forecast_service.py::test_direction_uncertain_when_band_straddles -x` | ❌ W0 | ⬜ pending |
| 7-01-04 | 01 | 0 | PROD-03 | unit | `pytest tests/test_forecast_service.py::test_direction_up_only_when_band_above -x` | ❌ W0 | ⬜ pending |
| 7-01-05 | 01 | 0 | PROD-04 | unit | `pytest tests/test_forecast_service.py::test_interval_correction_v3_default -x` | ❌ W0 | ⬜ pending |
| 7-01-06 | 01 | 0 | PROD-05 | unit | `pytest tests/test_forecast_service.py::test_data_freshness_fields -x` | ❌ W0 | ⬜ pending |
| 7-01-07 | 01 | 0 | PROD-05 | unit | `pytest tests/test_forecast_service.py::test_is_stale_threshold -x` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | PROD-05 | unit (Vitest) | `cd frontend && npx vitest run src/app/forecast` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 1 | PROD-02 | unit (Vitest) | `cd frontend && npx vitest run src/app/forecast` | ❌ W0 | ⬜ pending |
| 7-02-03 | 02 | 1 | PROD-03 | unit (Vitest) | `cd frontend && npx vitest run src/app/forecast` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_forecast_service.py` — add 7 new test functions:
  - `test_corrupted_model_blocked` — PROD-01
  - `test_direction_uncertain_when_band_straddles` — PROD-03
  - `test_direction_up_only_when_band_above` — PROD-03
  - `test_interval_correction_v3_default` — PROD-04
  - `test_data_freshness_fields` — PROD-05
  - `test_is_stale_threshold` — PROD-05
  - Extend `test_response_schema_fields` to check new fields — PROD-05
- [ ] `frontend/src/app/forecast/__tests__/page.test.tsx` — new Vitest test file:
  - Test stale banner renders when `is_stale=true`
  - Test chart hidden when `confidence_colour="Red"`
  - Test UNCERTAIN badge renders for `direction="uncertain"`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Stale banner visually appears above chart | PROD-05 | Visual layout verification | Load forecast for commodity with `last_data_date` > 30 days ago; confirm yellow banner appears above the chart |
| Red-badge commodity shows no chart | PROD-02 | UI render state | Load forecast for corrupted commodity; confirm no forecast chart is rendered, only "Insufficient data" message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
