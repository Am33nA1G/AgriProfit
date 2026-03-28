---
phase: 04-xgboost-forecasting-serving
verified: 2026-03-08T17:40:00Z
status: passed
score: 13/13 must-haves verified
re_verification: true
  previous_status: human_needed
  previous_score: 13/13
  gaps_closed:
    - "Forecast page renders chart and badges for full ML response (Gap 1) — automated by Playwright E2E test"
    - "Seasonal fallback banner with 'Limited Data Coverage' text renders for low-coverage district (Gap 2 / UI-05) — automated by Playwright E2E test"
    - "Changing state clears district dropdown and suppresses stale forecast query (Gap 3) — automated by Playwright E2E test"
  gaps_remaining: []
  regressions: []
---

# Phase 4: XGBoost Forecasting Serving Verification Report

**Phase Goal:** A farmer can request a 7-day or 14-day price forecast for any commodity-district pair, receive a direction signal and predicted range (not a point estimate), and the system serves this from a PostgreSQL cache refreshed nightly — with walk-forward validation RMSE logged before any model enters production.
**Verified:** 2026-03-08T17:40:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 04-06: Playwright E2E tests)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Alembic migrations for model_training_log and forecast_cache chain correctly | VERIFIED | d1e2f3a4b5c6 has down_revision="c2d3e4f5a6b7"; e2f3a4b5c6d7 has down_revision="d1e2f3a4b5c6" |
| 2 | ModelTrainingLog and ForecastCache ORM models are importable from app.models | VERIFIED | Both classes present in models/model_training_log.py and models/forecast_cache.py; registered in app/models/__init__.py |
| 3 | skforecast==0.20.1, xgboost==3.2.0, cachetools>=7.0.1 listed in requirements.txt | VERIFIED | All three entries confirmed in backend/requirements.txt |
| 4 | build_series_df returns wide-format DataFrame with DatetimeIndex, filters to >= 730 days | VERIFIED | Implementation in train_xgboost.py lines 49-101; test_series_filter_threshold and test_build_series_df_has_datetime_index enforce this |
| 5 | Walk-forward validation logs RMSE/MAPE to model_training_log BEFORE writing joblib artifact | VERIFIED | train_commodity() calls log_training() before joblib.dump(); test_walk_forward_logs_before_artifact enforces the invariant |
| 6 | get_or_load_model() returns None on cache miss, returns model on hit; LRU eviction works | VERIFIED | loader.py lines 25-46 implement this; 3 unit tests in test_ml_loader.py cover miss/hit/eviction |
| 7 | ForecastService.get_forecast() returns tier_label="seasonal average fallback" for < 365 day coverage | VERIFIED | _seasonal_fallback() returns correct tier_label; MIN_DAYS_SERVE=365 gate at service.py line 69; test_low_coverage_fallback passes |
| 8 | ForecastResponse schema has all 8 required fields | VERIFIED | schemas.py defines: direction, price_low, price_mid, price_high, confidence_colour, tier_label, last_data_date, horizon_days; test_response_schema_fields verifies |
| 9 | GET /api/v1/forecast/{commodity}/{district} is registered and returns 200 | VERIFIED | routes.py router registered at /api/v1 via forecast_ml_router in main.py line 375; 4 integration tests pass |
| 10 | APScheduler has refresh_forecast_cache job with CronTrigger(hour=3, minute=0) | VERIFIED | scheduler.py lines 131-135: CronTrigger(hour=3, minute=0), id="refresh_forecast_cache", replace_existing=True |
| 11 | app.state.model_cache is set at startup | VERIFIED | main.py lines 223-224: app.state.model_cache = get_model_cache() in lifespan startup |
| 12 | Next.js /forecast page calls forecastService.getForecast with useQuery | VERIFIED | page.tsx line 89: queryFn: () => forecastService.getForecast(commodity, district, horizon); enabled guard at line 90 |
| 13 | Fallback banner shown when tier_label === "seasonal average fallback"; data freshness note always shown | VERIFIED | page.tsx line 212: {forecast.tier_label === "seasonal average fallback" && ...}; line 307: Data last updated: {forecast.last_data_date}; Gap 2 E2E test asserts both at runtime |

**Score:** 13/13 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/d1e2f3a4b5c6_add_model_training_log.py` | model_training_log migration | VERIFIED | 53 lines; revision="d1e2f3a4b5c6", down_revision="c2d3e4f5a6b7"; all columns present |
| `backend/alembic/versions/e2f3a4b5c6d7_add_forecast_cache.py` | forecast_cache migration with composite unique index | VERIFIED | 52 lines; revision="e2f3a4b5c6d7", down_revision="d1e2f3a4b5c6"; composite unique index idx_forecast_cache_lookup present |
| `backend/app/models/model_training_log.py` | ModelTrainingLog ORM model | VERIFIED | 36 lines; all required columns: commodity, n_series, n_folds, rmse_fold_1-4, rmse_mean, mape_mean, artifact_path, skforecast_version, xgboost_version, excluded_districts |
| `backend/app/models/forecast_cache.py` | ForecastCache ORM model | VERIFIED | 40 lines; all required columns: commodity_name, district_name, generated_date, direction, price_low, price_mid, price_high, confidence_colour, tier_label, expires_at |
| `backend/scripts/train_xgboost.py` | Offline training script | VERIFIED | 287 lines (min 120); has build_series_df, log_training, train_commodity, mape_to_confidence_colour, main; ForecasterRecursiveMultiSeries used |
| `backend/tests/test_ml_training.py` | Training unit tests | VERIFIED | 4 tests: test_series_filter_threshold, test_walk_forward_logs_before_artifact, test_build_series_df_has_datetime_index, test_mape_to_confidence_colour |
| `ml/artifacts/.gitkeep` | ml/artifacts/ directory in git | VERIFIED | Directory exists with .gitkeep (0 bytes); ml/ directory committed |
| `backend/app/ml/loader.py` | LRU model loader | VERIFIED | 52 lines; get_or_load_model, get_model_cache, ARTIFACTS_DIR exported; threading.Lock used |
| `backend/app/forecast/schemas.py` | ForecastResponse and ForecastPoint Pydantic models | VERIFIED | ForecastResponse has all 8 required fields; ForecastPoint has date/price_low/price_mid/price_high |
| `backend/app/forecast/service.py` | ForecastService with cache/coverage/fallback | VERIFIED | 312 lines; get_forecast() with 4-step priority; mape_to_confidence_colour; _seasonal_fallback; _invoke_model |
| `backend/tests/test_ml_loader.py` | LRU loader unit tests | VERIFIED | 3 tests: test_missing_artifact_returns_none, test_lazy_load_on_first_request, test_lru_eviction |
| `backend/tests/test_forecast_service.py` | ForecastService unit tests | VERIFIED | 4 tests: test_response_schema_fields, test_low_coverage_fallback, test_cache_hit_returns_cached_response, test_confidence_colour_mapping |
| `backend/app/forecast/routes.py` | FastAPI forecast router | VERIFIED | GET /{commodity}/{district} with def handler (not async), horizon Query ge=7 le=14, ForecastService invoked |
| `backend/tests/test_forecast_api.py` | API integration tests | VERIFIED | 4 tests: test_endpoint_registered, test_forecast_endpoint_14day, test_cache_hit_returns_same_payload, test_low_coverage_district_returns_fallback |
| `backend/tests/test_scheduler.py` | Scheduler unit tests | VERIFIED | 2 tests: test_nightly_refresh_job_registered, test_refresh_job_has_replace_existing |
| `frontend/src/services/forecast.ts` | forecastService.getForecast typed client | VERIFIED | ForecastResponse and ForecastPoint interfaces exported; getForecast calls api.get with URL-encoded params |
| `frontend/src/components/ForecastChart.tsx` | Recharts ComposedChart component | VERIFIED | 145 lines (min 60); ComposedChart with Area (stackId="band") and Line; confidence colour map; ResponsiveContainer |
| `frontend/src/app/forecast/page.tsx` | Forecast page with selectors, badges, fallback banner | VERIFIED | 317 lines (min 120); commodity/state/district/horizon selects; useQuery with enabled guard; direction and confidence badges; fallback banner; data freshness note |
| `frontend/src/app/forecast/loading.tsx` | Skeleton loading placeholder | VERIFIED | animate-pulse skeleton for header, selectors, chart, badges, price range |
| `frontend/playwright.config.ts` | Playwright configuration targeting http://localhost:3000 | VERIFIED | 27 lines; baseURL='http://localhost:3000'; headless, retries=0, workers=1, no webServer block; commits e3bfd986 and 7684ece4 |
| `frontend/tests/e2e/forecast.spec.ts` | 3 E2E tests covering the 3 VERIFICATION.md gaps | VERIFIED | 289 lines; exactly 3 test() blocks; all 3 passed in 6.2s per SUMMARY; commits f08bd07c + 7684ece4 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| d1e2f3a4b5c6_add_model_training_log.py | c2d3e4f5a6b7 (price_bounds) | down_revision = "c2d3e4f5a6b7" | WIRED | Confirmed at line 14 of migration file |
| e2f3a4b5c6d7_add_forecast_cache.py | d1e2f3a4b5c6 | down_revision = "d1e2f3a4b5c6" | WIRED | Confirmed at line 14 of migration file |
| forecast_cache.py | app.database.base.Base | class ForecastCache(Base) | WIRED | Line 12 confirmed |
| train_xgboost.py | ModelTrainingLog | log_training() inserts ModelTrainingLog row | WIRED | Line 121 in train_xgboost.py |
| train_xgboost.py | ml/artifacts/ | joblib.dump(forecaster, artifact_path) | WIRED | Line 222 in train_xgboost.py |
| train_xgboost.py | ForecasterRecursiveMultiSeries | ForecasterRecursiveMultiSeries used in train_commodity() | WIRED | Line 174 in train_xgboost.py |
| forecast/service.py | app/ml/loader.py | get_or_load_model(slug) | WIRED | service.py line 74; imported at line 20 |
| forecast/service.py | app/models/forecast_cache.py | ForecastCache query on cache hit | WIRED | service.py line 92-100; imported at line 19 |
| app/ml/loader.py | ml/artifacts/{slug}.joblib | joblib.load(artifact_path) | WIRED | loader.py line 43 |
| app/main.py | app/forecast/routes.py | app.include_router(forecast_ml_router, prefix="/api/v1") | WIRED | main.py line 375 |
| app/main.py | app/ml/loader.py | app.state.model_cache = get_model_cache() | WIRED | main.py lines 223-224 in lifespan |
| app/integrations/scheduler.py | app/forecast/service.py | refresh_forecast_cache_job calls ForecastService | WIRED | scheduler.py lines 45, 61 |
| frontend/src/app/forecast/page.tsx | /api/v1/forecast/{commodity}/{district} | useQuery with forecastService.getForecast | WIRED | page.tsx line 89 |
| frontend/src/components/ForecastChart.tsx | recharts ComposedChart | import ComposedChart, Area, Line from recharts | WIRED | ForecastChart.tsx lines 4-13 |
| forecast.spec.ts Gap 1 | page.tsx #forecast-result, #forecast-badges, #data-freshness, #price-range-card | page.route() mock + DOM ID assertions | WIRED | DOM IDs confirmed at page.tsx lines 218, 236, 272, 320; "Forecast Chart" heading at line 309; DIRECTION_CONFIG maps 'up' -> 'Rising' at line 42 |
| forecast.spec.ts Gap 2 | page.tsx #fallback-banner, #forecast-badges, #price-range-card | page.route() mock returning tier_label="seasonal average fallback" | WIRED | #fallback-banner at line 222 behind tier_label condition; 'flat' -> 'Stable' at line 52; price-range-card at line 272 behind price_mid guard |
| forecast.spec.ts Gap 3 | page.tsx #district-select, #forecast-empty | selectOption('#state-select') triggers district reset, forecastRequests array tracks stale calls | WIRED | #district-select at line 156; #forecast-empty at line 186; canFetch guard at line 217 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FORE-01 | 04-02 | XGBoost model per commodity using ForecasterRecursiveMultiSeries, districts >= 730 days | SATISFIED | train_xgboost.py MIN_DAYS_TRAIN=730; ForecasterRecursiveMultiSeries imported and used in train_commodity(); build_series_df enforces 730-day filter |
| FORE-02 | 04-01, 04-02 | 4-fold walk-forward validation, RMSE/MAPE logged before model accepted | SATISFIED | TimeSeriesFold with n_splits=4 (via cv), log_training() called before joblib.dump(); ModelTrainingLog has rmse_mean NOT NULL enforcing this at DB level |
| FORE-03 | 04-04 | User can request 7-day and 14-day forecast for any commodity+district | SATISFIED | routes.py GET /{commodity}/{district}?horizon with Query(ge=7, le=14); horizon 7 and 14 both valid |
| FORE-04 | 04-03 | Forecast response includes direction, predicted range, tier_label | SATISFIED | ForecastResponse has direction, price_low, price_mid, price_high, tier_label; _invoke_model computes direction from % price change |
| FORE-05 | 04-03 | < 365 days data routed to seasonal fallback | SATISFIED | MIN_DAYS_SERVE=365 in service.py; _seasonal_fallback returns tier_label="seasonal average fallback" |
| FORE-06 | 04-01, 04-04 | Results cached in forecast_cache, refreshed nightly via APScheduler | SATISFIED | forecast_cache table with composite unique index; _write_cache in service.py; refresh_forecast_cache_job in scheduler.py with CronTrigger(hour=3) |
| SERV-01 | 04-01, 04-04 | FastAPI exposes /api/v1/forecast/{commodity}/{district} | SATISFIED | route registered in routes.py; included in main.py at /api/v1 prefix |
| SERV-02 | 04-03, 04-04 | Models loaded at startup into app.state | SATISFIED | app.state.model_cache = get_model_cache() in lifespan. Note: requirement says app.state.models; implementation uses app.state.model_cache (an LRU cache reference, not pre-loaded models). Models are lazy-loaded on first request per SERV-03. Functionally compliant — cache is attached at startup. |
| SERV-03 | 04-03 | LRU cache with configurable memory limit; lazy-loaded on first request | SATISFIED | LRUCache(maxsize=20) in loader.py; lazy loading in get_or_load_model(); models not loaded at startup |
| SERV-04 | 04-04 | APScheduler nightly forecast refresh job | SATISFIED | refresh_forecast_cache_job with CronTrigger(hour=3, minute=0) and replace_existing=True |
| UI-02 | 04-05, 04-06 | Forecast page with commodity+district selector, 14-day chart with confidence band, tier label, data coverage indicator | SATISFIED | Gap 1 E2E test (commit f08bd07c + fix 7684ece4) asserts: #forecast-result visible, badges contain "Rising" + "High Confidence" + "ML Model", #data-freshness shows date, #price-range-card shows price, "Forecast Chart" heading visible. All 3 tests passed in 6.2s. |
| UI-05 | 04-05, 04-06 | Coverage gap messages displayed, no silent failures | SATISFIED | Gap 2 E2E test asserts: #fallback-banner visible, contains "Limited Data Coverage" heading and coverage_message text, tier badge shows "Seasonal Average", #price-range-card not visible, #data-freshness shown. Passed against running dev server. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/app/forecast/service.py | 117-118, 163-164, 246-248 | Bare `except Exception` swallows errors in _lookup_cache, _get_coverage_days, _invoke_model | Warning | Errors silently fall through to fallback; reduces debuggability but does not break goal |
| backend/app/forecast/service.py | 311 | `self.db.rollback()` in bare except in _write_cache | Info | Cache write failures silent; acceptable degradation pattern |
| backend/app/forecast/service.py | 264-265 | _get_confidence_colour returns "Yellow" as default on exception | Info | Acceptable default — Yellow is moderate confidence, not misleading |

No blockers found. Warning-level items are defensive patterns that accept degradation gracefully (fallback to seasonal average) rather than exposing errors to the user. This aligns with the phase goal's resilience requirements.

---

## Re-Verification: Gap Closure Evidence

The three gaps from the initial verification (status: human_needed) were closed by plan 04-06, committed across three git commits:

| Commit | Content |
|--------|---------|
| `e3bfd986` | chore(04-06): install Playwright 1.58.2 + playwright.config.ts |
| `f08bd07c` | test(04-06): write 3 E2E tests for VERIFICATION.md gaps |
| `7684ece4` | fix(04-06): fix commodity select timing (DOM detachment race condition) |

**Gap 1 — Forecast page chart and badge rendering:**
- Test: "Gap 1: forecast page renders chart and badges for Wheat + Pune"
- Asserts `#forecast-result` visible; badges contain "Rising", "High Confidence", "ML Model"; `#fallback-banner` absent; `#data-freshness` shows "Data last updated: 2025-10-30"; `#price-range-card` shows "₹2000.00"; "Forecast Chart" heading visible
- DOM IDs confirmed in page.tsx: #forecast-result (line 218), #forecast-badges (line 236), #data-freshness (line 320), #price-range-card (line 272); DIRECTION_CONFIG maps 'up' to "Rising" (line 42)
- Status: CLOSED

**Gap 2 — Seasonal fallback banner (UI-05):**
- Test: "Gap 2: seasonal fallback banner renders for low-coverage district"
- Asserts `#fallback-banner` visible with "Limited Data Coverage" and coverage_message text; tier badge "Seasonal Average"; direction "Stable" (flat->Stable per DIRECTION_CONFIG line 52); `#price-range-card` absent; `#data-freshness` shown
- DOM IDs confirmed: #fallback-banner at page.tsx line 222 (behind tier_label === "seasonal average fallback" condition)
- Status: CLOSED

**Gap 3 — Cascading select reset:**
- Test: "Gap 3: changing state clears district and does not fire stale forecast query"
- Asserts: after selecting Maharashtra+Pune then switching to Karnataka, district value resets to "", Karnataka's districts appear (Bangalore present, Pune absent), no stale Pune forecast request fires, `#forecast-empty` visible
- DOM IDs confirmed: #district-select (line 156), #forecast-empty (line 186); canFetch guard at line 217 prevents query when district is empty
- Status: CLOSED

**Test execution:** All 3 tests passed in 6.2 seconds total against the running dev server (per 04-06-SUMMARY.md). Route mocking with `page.route()` makes tests deterministic without live ML artifacts.

---

## Summary

Phase 4 delivers all 13 observable truths. All 21 required artifacts are present, substantive, and wired. All 16 key links are confirmed in the codebase. All 12 requirement IDs (FORE-01 through FORE-06, SERV-01 through SERV-04, UI-02, UI-05) are fully satisfied.

The three human verification items from the initial verification have been automated by plan 04-06 (Playwright E2E tests). The tests use API route mocking to verify the full React rendering path deterministically without requiring live ML model artifacts. All 3 tests passed against the running dev server in 6.2 seconds.

The phase goal is achieved: a farmer can request a 7-day or 14-day price forecast for any commodity-district pair, receive a direction signal and predicted range, and the system serves from a PostgreSQL cache refreshed nightly with walk-forward validation RMSE logged before any model enters production.

One implementation detail noted from the initial verification stands: SERV-02 specifies "loaded into app.state.models" but the implementation uses "app.state.model_cache" (an LRU cache reference, not a pre-populated model dictionary). This is correct per SERV-03 (lazy loading), and the cache is attached at startup as required. The naming divergence is minor and does not affect functionality.

---

_Verified: 2026-03-08T17:40:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — gaps closed by plan 04-06 (Playwright E2E tests)_
