# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** A farmer in any district can ask "what should I grow and when should I sell it?" and get a data-backed answer.
**Current focus:** Phase 1 — District Harmonisation + Price Cleaning

## Current Position

Phase: 1 of 6 (District Harmonisation + Price Cleaning)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-03-01 — Roadmap created; 6-phase ML intelligence milestone defined

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: District harmonisation is Phase 1 — hard dependency for all ML features; state-scoped RapidFuzz matching required (global matching achieves only 47.5% accuracy on Hindi names)
- [Roadmap]: LSTM is v2 — XGBoost baseline must be validated (walk-forward RMSE logged) before LSTM begins
- [Roadmap]: Phases 5 and 6 are independent of each other and can run in parallel after Phase 4 completes
- [Roadmap]: Soil advisor is rule-based ICAR lookup, not a live ML model — precomputed suitability scores, never field-level claims
- [Roadmap]: Arbitrage threshold (10% net margin) is a configurable parameter, not a hardcoded constant

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4 readiness]: Determine how many commodity-district pairs meet the 730-day training threshold before committing to launch scope; if fewer than expected, the seasonal fallback must be fully tested before Phase 4 ships
- [Data freshness]: Price data ends 2025-10-30; 4+ month gap to 2026-03-01 must be communicated in UI and considered in holdout validation design
- [Phase 5 planning]: NPK/pH crop suitability thresholds need sourcing from ICAR guidelines (1-2 hour targeted research task during Phase 5 planning)

## Session Continuity

Last session: 2026-03-01
Stopped at: Roadmap created — ROADMAP.md, STATE.md, and REQUIREMENTS.md traceability written
Resume file: None
