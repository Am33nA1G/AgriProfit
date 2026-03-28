---
phase: 05-soil-crop-advisor
plan: "01"
subsystem: soil-advisor-backend
tags: [soil, crop-suitability, fertiliser, alembic, tdd, pure-functions, seeder]
dependency_graph:
  requires: []
  provides:
    - soil_profiles table (Alembic migration e1f2a3b4c5d6)
    - soil_crop_suitability table (Alembic migration e1f2a3b4c5d6)
    - app.soil_advisor.suitability (COVERED_STATES, rank_crops, is_deficient, score_crop)
    - app.soil_advisor.fertiliser (FERTILISER_ADVICE, generate_fertiliser_advice)
    - scripts/seed_soil_suitability.py (bulk CSV seeder, idempotent)
  affects:
    - Phase 05 Plan 02 (FastAPI endpoint that reads from soil_profiles and calls rank_crops)
tech_stack:
  added:
    - SQLAlchemy + Alembic (new tables soil_profiles, soil_crop_suitability)
    - pandas (used in seeding script for CSV ingestion)
  patterns:
    - Pure-function TDD (RED -> GREEN, zero database calls in tested modules)
    - ON CONFLICT upsert for idempotent seeding
    - 3-tier tolerance scoring (low/medium/high crop tolerance against soil deficiency)
key_files:
  created:
    - backend/alembic/versions/e1f2a3b4c5d6_add_soil_advisor_tables.py
    - backend/app/soil_advisor/__init__.py
    - backend/app/soil_advisor/suitability.py
    - backend/app/soil_advisor/fertiliser.py
    - backend/scripts/seed_soil_suitability.py
    - backend/tests/test_soil_suitability.py
    - backend/tests/test_soil_fertiliser.py
  modified: []
decisions:
  - "down_revision set to both current heads (4be60c2d7319, e2f3a4b5c6d7) instead of c2d3e4f5a6b7 — plan had stale down_revision since two new Phase 4 migrations were added after the plan was written"
  - "score_crop uses 3-tier scoring: low-tolerance crops receive +1.0 base bonus for thriving in deficient soil; medium-tolerance returns 0 when deficient; high-tolerance returns 0 when deficient"
  - "pH excluded from FERTILISER_ADVICE by design — pH is a range check requiring on-site testing, not a deficiency that responds to a single fertiliser"
  - "rank_crops returns crop_row dicts extended with score key (immutable pattern — new dict via {**row, score: s})"
metrics:
  duration_minutes: 4
  tasks_completed: 4
  tasks_total: 4
  files_created: 7
  files_modified: 0
  tests_added: 17
  tests_passed: 17
  completed_date: "2026-03-03"
---

# Phase 05 Plan 01: Soil Advisor Backend Foundation Summary

**One-liner:** ICAR-based soil crop suitability engine with pure-function TDD — Alembic migration for soil_profiles/soil_crop_suitability tables, rank_crops() 3-tier tolerance scoring, fertiliser advice cards (N/P/K/OC), and idempotent CSV bulk seeder for 9,643 soil health files.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Alembic migration for soil_profiles and soil_crop_suitability | ab0a118 | backend/alembic/versions/e1f2a3b4c5d6_add_soil_advisor_tables.py |
| 2 | soil_advisor module scaffold + seeding script | 44df27e | backend/app/soil_advisor/__init__.py, backend/scripts/seed_soil_suitability.py |
| 3 | Write test files (RED phase) | c193a0f | backend/tests/test_soil_suitability.py, backend/tests/test_soil_fertiliser.py |
| 4 | Implement suitability.py and fertiliser.py (GREEN phase) | b2df31e | backend/app/soil_advisor/suitability.py, backend/app/soil_advisor/fertiliser.py |

## Verification Results

```
pytest tests/test_soil_suitability.py tests/test_soil_fertiliser.py -v
17 passed, 1 warning in 0.24s
```

All success criteria met:
- e1f2a3b4c5d6_add_soil_advisor_tables.py: correct down_revision merging both heads
- COVERED_STATES: exactly 21 states, all uppercase
- rank_crops(): N-tolerant crops rank higher in N-deficient blocks, max 5 results, zero scores excluded
- generate_fertiliser_advice(): strict > 50 threshold, no pH in output
- seed_soil_suitability.py: batch inserts (chunks of 500), ON CONFLICT upsert, state/district in ALLCAPS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected stale down_revision in Alembic migration**
- **Found during:** Task 1
- **Issue:** Plan specified `down_revision = "c2d3e4f5a6b7"` (price_bounds migration), but two Phase 4 migrations had been added after the plan was written — the actual current heads are `4be60c2d7319` (merge_heads) and `e2f3a4b5c6d7` (add_forecast_cache). Using the stale revision would have broken the Alembic migration chain.
- **Fix:** Set `down_revision = ("4be60c2d7319", "e2f3a4b5c6d7")` to merge both current heads, following the same pattern as the existing `4be60c2d7319_merge_heads.py`.
- **Files modified:** backend/alembic/versions/e1f2a3b4c5d6_add_soil_advisor_tables.py
- **Commit:** ab0a118

## Self-Check: PASSED

### Files Exist

All 7 created files confirmed present on disk.

### Commits Verified

| Hash | Message |
|------|---------|
| ab0a118 | feat(05-01): add Alembic migration for soil_profiles and soil_crop_suitability tables |
| 44df27e | feat(05-01): soil_advisor module scaffold and seed_soil_suitability.py bulk seeder |
| c193a0f | test(05-01): add failing RED phase tests for suitability.py and fertiliser.py |
| b2df31e | feat(05-01): implement suitability.py and fertiliser.py (GREEN phase) |
