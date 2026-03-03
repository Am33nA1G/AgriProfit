---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-03T07:28:00.000Z"
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 16
  completed_plans: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** A farmer in any district can ask "what should I grow and when should I sell it?" and get a data-backed answer.
**Current focus:** Phase 2 — Seasonal Price Calendar — Plan 01 complete; Plan 02 (FastAPI endpoint + frontend) is next

## Current Position

Phase: 2 of 6 (Seasonal Price Calendar) — In Progress
Plan: 1 of 2 in current phase — COMPLETE
Status: Phase 02 Plan 01 complete — seasonal_price_stats migration applied, aggregator module implemented, 10 unit tests pass GREEN, train_seasonal.py syntax valid
Last activity: 2026-03-03 — Plan 02-01 complete: seasonal aggregation pipeline (commits: 45e5b7b, 0cdaf56, 3240b98)

Progress: [████████░░] 50% (8/16 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 6.6 min
- Total execution time: 0.70 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 | 3/3 | 26 min | 8.7 min |
| Phase 02 | 1/2 | 15 min | 15 min |
| Phase 03 | 2/2 | 8 min | 4.0 min |
| Phase 05 | 2/2 | 15 min | 7.5 min |

**Recent Trend:**
- Last 5 plans: 4 min (03-02), 4 min (05-01), 11 min (05-02), 7 min (06-01), 5 min (06-02)
- Trend: Stable

*Updated after each plan completion*
| Phase 05 P02 | 11 | 2 tasks | 8 files |
| Phase 06-mandi-arbitrage-dashboard P01 | 7 | 3 tasks | 10 files |
| Phase 06-mandi-arbitrage-dashboard P02 | 5 | 3 tasks | 4 files |
| Phase 02-seasonal-price-calendar P01 | 15 | 3 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: District harmonisation is Phase 1 — hard dependency for all ML features; state-scoped RapidFuzz matching required (global matching achieves only 47.5% accuracy on Hindi names)
- [Roadmap]: LSTM is v2 — XGBoost baseline must be validated (walk-forward RMSE logged) before LSTM begins
- [Roadmap]: Phases 5 and 6 are independent of each other and can run in parallel after Phase 4 completes
- [Roadmap]: Soil advisor is rule-based ICAR lookup, not a live ML model — precomputed suitability scores, never field-level claims
- [Roadmap]: Arbitrage threshold (10% net margin) is a configurable parameter, not a hardcoded constant
- [Phase 01]: pyarrow 17.0.0 used instead of 19.0.0: price parquet incompatible with pyarrow 19 (Repetition level histogram size mismatch)
- [Phase 01]: rapidfuzz_utils.default_process processor required for district matching: WRatio without processor gives ~20/100 for case-mismatched district names (BANKA vs Banka)
- [Phase 01]: Weather data matched globally (no state column): weather CSV has district column only; global matching with state assigned from canonical match
- [Phase 01]: Coverage metric is price-district-centric: 557/571 price districts have rainfall match (97.5%) vs 90.7% from rainfall perspective
- [Phase 01]: pandas 2.x groupby loop pattern: explicit for-loop over groupby() produces correct dict-of-rows DataFrame; groupby().apply(fn) returning pd.Series creates MultiIndex in pandas 2.x
- [Phase 01]: IQR multiplier 3x confirmed as planned: captures unit-corruption outliers without capping legitimate premium commodity prices
- [Phase 01]: price_history.modal_price never modified: bounds stored in price_bounds table; downstream clips at read time preserving full audit trail
- [Phase 01]: HARM-04 was a documentation correction not a code fix — harmonise_districts.py always correctly processed available 21 states; requirement text had overstated local dataset as 31 states
- [Phase 01]: SOIL-05 UI label "Available for 31 states" intentionally left unchanged — concerns future Phase 5 UI messaging, not Phase 1 data harmonisation
- [Phase 03]: pandas 3.0.1 + numpy 2.4.2 installed into venv (were missing) for pure-Python feature engineering
- [Phase 03]: All feature functions are pure Python — DataFrames in, DataFrames out; zero database calls; testable without running DB
- [Phase 03]: cutoff_date enforced INSIDE price feature function (series.loc[:cutoff_date]) — caller cannot bypass structural anti-leakage
- [Phase 03]: Daily reindex + ffill before shift() required for irregular price series — shift(N) on market-day-only data shifts by N records not N calendar days
- [Phase 03]: Tier B weather districts return empty DataFrame, not NaN-filled — XGBoost handles NaN natively; imputing would create false signal for ~310 districts
- [Phase 05]: Alembic down_revision corrected to merge both current heads (4be60c2d7319, e2f3a4b5c6d7) — plan had stale single-revision reference to c2d3e4f5a6b7
- [Phase 05]: score_crop 3-tier scoring: low-tolerance crops receive +1.0 base bonus for thriving in deficient soil; medium/high-tolerance crops return 0.0 when block is deficient
- [Phase 05]: pH excluded from FERTILISER_ADVICE by design — pH range check requires on-site testing, not a single fertiliser recommendation
- [Phase 05]: Query params used for state/district/block on /profile endpoint to handle block names containing hyphens/spaces (e.g., ANANTAPUR - 4689)
- [Phase 05]: CSS percentage-width divs for nutrient bars instead of Recharts — simpler, mobile-friendly, DOM-testable
- [Phase 05]: rank_crops() aggregates scores by crop_name before ranking — soil_crop_suitability has one row per (crop_name, nutrient), causing duplicate React keys without aggregation
- [Phase 05]: SoilDisclaimer renders with no dismiss/close button — mandatory non-dismissable by plan spec
- [Phase 05]: Coverage gate (COVERED_STATES) applied only to /profile, not /districts or /blocks — lists return empty arrays
- [Phase 06]: freight_cost_per_quintal = costs.total_cost directly: compare_mandis() called with quantity_kg=100, so costs.total_cost is already the per-quintal cost
- [Phase 06]: Stale results are INCLUDED with is_stale=True — never silently dropped; only margin threshold causes suppression
- [Phase 06]: Arbitrage route handler is def (not async def) — OSRM blocks event loop, FastAPI runs sync handlers in thread pool
- [Phase 06-mandi-arbitrage-dashboard]: Simple text inputs (not Select dropdowns) used for commodity and district on arbitrage page — keeps complexity low per plan spec
- [Phase 06-mandi-arbitrage-dashboard]: VerdictBadge uses className colour overrides because shadcn Badge variant=default maps to primary colour not green
- [Phase 06-mandi-arbitrage-dashboard]: enabled: submitted && !!commodity && !!district — TanStack Query fires only after form submit; setSubmitted(false) on input change forces fresh query on next submission
- [Phase 06-mandi-arbitrage-dashboard]: Human verification confirmed ARB-02 suppressed empty state — Wheat/Ernakulam correctly shows "All 50 results were below the 10% net margin threshold" with no crash
- [Phase 02-01]: compute_seasonal_stats() is a pure function — no DB calls inside function body; load_and_prepare() and upsert_seasonal_stats() handle all I/O
- [Phase 02-01]: is_best/is_worst labels only set when years_of_data >= 3 — sparse series never get best/worst labels to avoid misleading farmers
- [Phase 02-01]: month_rank=1 means highest median_price (rank descending by price); top-2 months get is_best=True, bottom-1 gets is_worst=True
- [Phase 02-01]: train_seasonal.py not run during plan execution — requires live PostgreSQL with price_bounds populated and 25M row parquet; script validated via ast.parse() only

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4 readiness]: Determine how many commodity-district pairs meet the 730-day training threshold before committing to launch scope; if fewer than expected, the seasonal fallback must be fully tested before Phase 4 ships
- [Data freshness]: Price data ends 2025-10-30; 4+ month gap to 2026-03-01 must be communicated in UI and considered in holdout validation design
- [Phase 5 Plan 02]: soil_profiles table must be populated via seed_soil_suitability.py before the endpoint can return results; developer must run the seeder after applying the migration

## Session Continuity

Last session: 2026-03-03
Stopped at: Phase 02 Plan 01 complete — seasonal aggregation pipeline: migration, aggregator, 10 tests, train_seasonal.py
Resume file: None
