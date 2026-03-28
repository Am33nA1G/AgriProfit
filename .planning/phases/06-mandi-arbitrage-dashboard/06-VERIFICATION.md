---
phase: 06-mandi-arbitrage-dashboard
verified: 2026-03-03T07:41:30Z
status: passed
score: 10/10 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Navigate to /arbitrage in browser, confirm Sidebar/Navbar has no direct link to /arbitrage"
    expected: "Page is reachable by direct URL but absent from navigation menu"
    why_human: "Sidebar and Navbar do not contain /arbitrage — page is an orphan in the UI nav. Human must confirm whether this is intentional (URL-only access) or a missing nav entry."
---

# Phase 6: Mandi Arbitrage Dashboard Verification Report

**Phase Goal:** A farmer can select a commodity and their origin district and see the top 3 destination mandis ranked by net profit after freight and spoilage — using only price data fresher than 7 days, with stale data flagged rather than displayed as current.

**Verified:** 2026-03-03T07:41:30Z
**Status:** PASSED (with one informational note on navigation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/v1/arbitrage/{commodity}/{district} returns top 3 mandis ranked by net_profit_per_quintal descending | VERIFIED | `service.py` sorts `passing` list by `net_profit_per_quintal` descending, slices `[:3]`; test `test_returns_top_3_ranked` PASSED |
| 2 | Results with net margin below 10% threshold are suppressed; suppressed_count is returned | VERIFIED | `service.py` computes `margin_pct = (net_profit/gross_revenue)*100`; increments `suppressed_count` and `continue`s; `test_margin_threshold_filters_results` and `test_all_suppressed_returns_empty` PASSED. Human-confirmed: Wheat/Ernakulam shows "All 50 results were below the 10% net margin threshold" |
| 3 | Freshness uses MAX(price_date) — never date.today() | VERIFIED | `service.py`: `data_reference_date = max(known_dates)` from returned mandis; `_query_max_price_date()` is the DB fallback (not `date.today()`); `test_reference_date_is_max_price_date` PASSED |
| 4 | Each result contains distance_km, travel_time_hours, freight_cost_per_quintal, spoilage_percent, net_profit_per_quintal | VERIFIED | `ArbitrageResult` schema requires all 5 fields (no defaults); `test_result_fields_complete` PASSED; integration test `test_response_has_required_fields` validates all 5 in JSON response |
| 5 | Stale results (days_since_update > 7) returned with is_stale=True and stale_warning populated — not silently dropped | VERIFIED | `service.py`: stale mandis append to `passing[]` with `is_stale=True`; only margin threshold causes suppression; `test_7day_freshness_gate` and `test_stale_results_have_warning` PASSED |
| 6 | User can select commodity + district from inputs and click Find Opportunities to trigger the API call | VERIFIED | `page.tsx`: `useState` for commodity/district/submitted; form `onSubmit` sets `submitted=true`; `useQuery` enabled only when `submitted && !!commodity && !!district`; `test_selectors_render` PASSED |
| 7 | Top 3 results render in table with mandi name, district, distance, travel time, freight, spoilage, net profit, verdict badge | VERIFIED | `ResultsTable` component renders 8-column Table; `VerdictBadge` component uses colour-overriding className; `test_results_table_shown_on_data` PASSED |
| 8 | Yellow banner appears when has_stale_data=true showing data_reference_date | VERIFIED | `page.tsx`: `data?.has_stale_data && <Alert>Data last updated {data.data_reference_date}...`; `test_stale_banner_shown` PASSED |
| 9 | When results empty and suppressed_count > 0, informative threshold message shown — not blank page | VERIFIED | `ResultsTable`: `if (results.length === 0 && suppressed_count > 0)` returns yellow border div with threshold message; `test_suppressed_empty_state` PASSED; human-confirmed |
| 10 | When no coverage, informative empty-state shown — not a crash | VERIFIED | `ResultsTable`: `else` branch returns grey border div with "No arbitrage opportunities found"; `test_generic_empty_state` PASSED |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/arbitrage/__init__.py` | Package init | VERIFIED | Exists (empty — correct) |
| `backend/app/arbitrage/schemas.py` | ArbitrageResult and ArbitrageResponse Pydantic models | VERIFIED | Both classes present; all required fields exist including the 5 ARB-04 fields; `max_length=3` constraint on results list |
| `backend/app/arbitrage/service.py` | get_arbitrage_results() with freshness gate, margin threshold, top-3 ranking | VERIFIED | Full implementation: 6 steps documented in docstring; 179 lines; no stubs |
| `backend/app/arbitrage/routes.py` | GET /arbitrage/{commodity}/{district} FastAPI route handler | VERIFIED | `def get_arbitrage_signals` (sync, not async — OSRM protection confirmed); error mapping: ValueError("not found") → 404, other ValueError → 400, Exception → 500 |
| `backend/tests/test_arbitrage_service.py` | Unit tests for ARB-01 through ARB-04 behaviours | VERIFIED | 11 tests (4 schema + 7 service); all 11 PASSED |
| `backend/tests/test_arbitrage_api.py` | Integration tests via TestClient | VERIFIED | 7 tests; all 7 PASSED |
| `backend/app/transport/schemas.py` | MandiComparison with latest_price_date field | VERIFIED | Line 268: `latest_price_date: date | None = Field(default=None, ...)` — backward-compatible |
| `backend/app/core/config.py` | arbitrage_margin_threshold_pct setting | VERIFIED | Line 356: `arbitrage_margin_threshold_pct: float = Field(default=10.0, ge=0.0, le=50.0, ...)` |
| `backend/app/main.py` | arbitrage_router imported and registered | VERIFIED | Line 56: `from app.arbitrage.routes import router as arbitrage_router`; Line 377: `app.include_router(arbitrage_router, prefix="/api/v1")`; "Arbitrage" tag metadata present |
| `frontend/src/services/arbitrage.ts` | arbitrageService.getResults() typed API call | VERIFIED | Exports `ArbitrageResult`, `ArbitrageResponse`, `arbitrageService`; uses `api.get` with `encodeURIComponent` on both path params |
| `frontend/src/app/arbitrage/page.tsx` | ArbitragePage with selectors, table, banner | VERIFIED | 283 lines; full implementation with `ResultsTable` subcomponent, `VerdictBadge`, stale Alert, two empty states |
| `frontend/src/app/arbitrage/loading.tsx` | Next.js loading boundary skeleton | VERIFIED | Exists; 7 lines; renders "Searching for arbitrage opportunities..." |
| `frontend/src/app/arbitrage/__tests__/page.test.tsx` | Vitest tests for UI-04 and UI-05 | VERIFIED | 5 tests; all 5 PASSED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/arbitrage/routes.py` | `get_arbitrage_results()` | Direct call in sync route handler | WIRED | `return get_arbitrage_results(commodity=..., district=..., db=..., max_distance_km=...)` |
| `backend/app/arbitrage/service.py` | `compare_mandis()` | TransportCompareRequest with quantity_kg=100 | WIRED | `comparisons, has_estimated = compare_mandis(request, db)` — quantity_kg=100.0 confirmed |
| `backend/app/main.py` | `arbitrage_router` | `app.include_router(arbitrage_router, prefix="/api/v1")` | WIRED | Line 377 confirmed |
| `backend/app/transport/schemas.MandiComparison` | `latest_price_date` | Populated in `compare_mandis()` from `price_analytics_map` | WIRED | `transport/service.py` lines 579-618: `latest_price_date=pa_entry.latest_price_date if pa_entry else None` |
| `frontend/src/app/arbitrage/page.tsx` | `arbitrageService.getResults()` | `useQuery({ queryFn: () => arbitrageService.getResults(...), enabled: submitted })` | WIRED | Confirmed in `page.tsx` lines 155-160 |
| `frontend/src/services/arbitrage.ts` | `GET /api/v1/arbitrage/{commodity}/{district}` | `api.get('/arbitrage/${encodeURIComponent(commodity)}/${encodeURIComponent(district)}')` | WIRED | Confirmed in `arbitrage.ts` lines 33-35 |
| `frontend/src/app/arbitrage/page.tsx` | Stale data banner | `data.has_stale_data === true` renders Alert with `data_reference_date` | WIRED | Lines 233-240 confirmed |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ARB-01 | 06-01 | Top 3 destination mandis ranked by net profit after freight + spoilage | SATISFIED | `service.py` sorts and slices top 3; `test_returns_top_3_ranked` PASSED; `test_successful_arbitrage` PASSED |
| ARB-02 | 06-01 | Signals only shown when net margin exceeds configurable threshold (default 10%) | SATISFIED | Margin gate in `service.py`; `arbitrage_margin_threshold_pct=10.0` in config; human-confirmed with Wheat/Ernakulam test |
| ARB-03 | 06-01 | Only data fresher than 7 days — stale data flagged rather than shown as current | SATISFIED | `data_reference_date = MAX(price_date)`; `is_stale = days_since > 7`; stale included with warning, not dropped; `test_7day_freshness_gate` PASSED |
| ARB-04 | 06-01 | Each result shows distance, travel time, freight cost, spoilage, net profit per quintal | SATISFIED | All 5 fields in `ArbitrageResult` schema; `test_result_fields_complete` and `test_response_has_required_fields` PASSED |
| UI-04 | 06-02 | Arbitrage dashboard with commodity + district selector, ranked mandi table, freshness indicator | SATISFIED | `ArbitragePage` with text inputs, 8-column table, `days_since_update` per-row, stale badge; `test_results_table_shown_on_data` PASSED |
| UI-05 | 06-02 | Coverage gap messages when feature unavailable — no silent failures | SATISFIED | Two distinct empty states: threshold-suppressed message and generic no-opportunities message; human-confirmed; `test_suppressed_empty_state` and `test_generic_empty_state` PASSED |

**All 6 required IDs accounted for. No orphaned requirements.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/arbitrage/service.py` | 177 | `return _date_cls.today()` | Info | Absolute last-resort fallback in `_query_max_price_date()`. Only triggered if DB query fails AND no known mandi price dates. Does not violate ARB-03 in normal operation. |

No stubs, placeholders, or empty implementations found. No TODO/FIXME/XXX comments in phase 6 files.

---

### Navigation Gap (Informational)

`frontend/src/components/layout/Sidebar.tsx` and `frontend/src/components/layout/Navbar.tsx` do not contain a link to `/arbitrage`. The page is accessible via direct URL navigation but is not surfaced in the application's side navigation or mobile menu. This does not break any ARB or UI requirement as stated, but reduces discoverability.

The plan's scope was to create the page at `/arbitrage` — it does not mandate nav registration. However, this is worth human confirmation that it is intentional.

---

### Human Verification Required

#### 1. Navigation reachability confirmation

**Test:** Open http://localhost:3000 after logging in. Check Sidebar (desktop) and hamburger menu (mobile) for an "Arbitrage" link.
**Expected:** No link exists — page is only reachable via direct URL http://localhost:3000/arbitrage
**Why human:** Sidebar and Navbar code grep confirmed no `/arbitrage` href. Human must decide whether this omission is intentional or a gap to address in a future task.

Note: Human has already confirmed the following are working visually:
- Wheat/Ernakulam correctly shows "All 50 results were below the 10% net margin threshold — no profitable arbitrage found" (ARB-02 suppressed empty state)
- Suppressed empty state UI renders correctly (UI-05)

---

### Test Results Summary

| Suite | Tests | Status |
|-------|-------|--------|
| `test_arbitrage_service.py` (unit) | 11/11 | ALL PASSED |
| `test_arbitrage_api.py` (integration) | 7/7 | ALL PASSED |
| `test_arbitrage/__tests__/page.test.tsx` (Vitest) | 5/5 | ALL PASSED |
| `test_transport_service.py` (backward compat) | 30/30 | ALL PASSED |
| `test_transport_api.py` (backward compat) | 5/5 | ALL PASSED |

Pre-existing backend test failures in `test_prices_api.py`, `test_users_api.py`, `test_notifications_api.py` (SQLite schema mismatch) were documented in 06-01-SUMMARY.md as pre-dating this phase and are out of scope.

---

### Gaps Summary

No gaps. All 10 observable truths verified. All 6 requirement IDs (ARB-01, ARB-02, ARB-03, ARB-04, UI-04, UI-05) satisfied with test evidence. All key links wired. No stubs or orphaned artifacts.

The only open item is informational: the `/arbitrage` page is not linked from the Sidebar or Navbar navigation, making it reachable only via direct URL. This is not a requirements violation but may warrant a future navigation update.

---

_Verified: 2026-03-03T07:41:30Z_
_Verifier: Claude (gsd-verifier)_
