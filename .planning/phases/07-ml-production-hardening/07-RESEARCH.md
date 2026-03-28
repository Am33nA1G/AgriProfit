# Phase 7: ML Production Hardening - Research

**Researched:** 2026-03-08
**Domain:** FastAPI ML serving layer, Pydantic schemas, Next.js React rendering
**Confidence:** HIGH — all findings are from direct code inspection of the live codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Corrupted model blocking (Fix 1)**
- Hard gate: if `prophet_mape > 5.0` in meta, the model is corrupted — never serve it
- Redirect silently to seasonal fallback (already exists in service.py)
- Response label: `"tier": "seasonal_average"` + `"confidence": "insufficient_data"`
- Do NOT show any forecast chart or direction signal for these
- 14 known corrupted v3 models; the gate must apply at serve time, not offline

**Confidence badge thresholds (Fix 2)**
- Current system uses arbitrary/unclear thresholds — replace entirely
- New thresholds tied to actual out-of-sample prophet_mape from meta:
  - Green: prophet_mape < 0.15 — model is reliable
  - Yellow: prophet_mape 0.15–0.35 — directional signal only, not a trading price
  - Red / Insufficient: prophet_mape > 0.35 OR corrupted (>5.0) — do not show forecast
- For Red: show "Insufficient data for [commodity] in [district] — seasonal pattern only"
- Do NOT show a chart with a Red badge. Remove the chart entirely for Red/insufficient.
- Frontend badge label changes: Green="Reliable", Yellow="Directional only", Red not shown (replaced by message)

**Direction signal suppression (Fix 3)**
- Current: always shows UP/DOWN/FLAT regardless of uncertainty
- New rule: only show UP or DOWN if the forecast uncertainty band does NOT straddle zero change
  - if `low_forecast > current_price` → UP is valid
  - if `high_forecast < current_price` → DOWN is valid
  - if band spans both sides → direction = "UNCERTAIN"
- "UNCERTAIN" renders as a neutral grey label, not a coloured arrow
- FLAT remains: when mid forecast within ±2% of current price
- This logic lives in `service.py` before returning ForecastResponse — not in the frontend

**Interval correction threshold (Fix 4)**
- Current threshold in `service.py`: apply correction if `interval_coverage < 0.70`
- Change to: apply correction if `interval_coverage < 0.80`
- Correction formula stays the same: `correction = 0.80 / interval_coverage`
- For v3 models (no interval_coverage in meta): assume 0.60 → always apply correction
- This widens bands for more models, making the displayed range more honest

**Stale data warning (Fix 5)**
- Compute `data_freshness_days = (today - last_data_date).days` at serve time
- Add `data_freshness_days: int` and `is_stale: bool` to ForecastResponse schema
- Stale threshold: `is_stale = data_freshness_days > 30`
- Backend always returns these fields — frontend decides how to render
- Frontend: if `is_stale`, show a yellow banner ABOVE the forecast chart
- Stale warning does NOT suppress the forecast — it accompanies it
- Data freshness must be shown even for Green-badge models

**Farmer-readable metadata (Fix 5 extension)**
- Add to ForecastResponse: `n_markets: int` (len(districts_list) from meta)
- Add to ForecastResponse: `typical_error_inr: float` (prophet_mape × current_price, rounded to nearest ₹10)
- Frontend shows below the chart: "Based on data from {n_markets} markets. Typical forecast error: ₹{typical_error_inr}/quintal."

**What NOT to change**
- Do not retrain any models
- Do not change the forecast API endpoint URL or request parameters
- Do not change the nightly scheduler
- Do not add new endpoints — extend existing ForecastResponse schema only
- Do not touch the seasonal calendar, soil advisor, or arbitrage pages

### Claude's Discretion

None specified — all 5 fixes are fully spec'd in the locked decisions.

### Deferred Ideas (OUT OF SCOPE)

- Full v4 retraining for all 256 commodities — Phase 8
- Walk-forward backtesting to validate direction accuracy — Phase 8
- Conformal prediction for properly calibrated intervals — Phase 8
- "Beat the naive baseline" gate before promoting to full model — Phase 8
- Farmer-facing explanation of why a forecast is low confidence — future UX phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROD-01 | No corrupted model (prophet_mape > 5.0) ever reaches the serving layer — redirected to seasonal fallback with "Insufficient data" label | Fix 1: gate in `get_forecast()` before `_invoke_model()`, using `load_meta()` result |
| PROD-02 | Confidence badge derived from actual prophet MAPE thresholds: Green < 0.15, Yellow 0.15–0.35, Red > 0.35 | Fix 2: replace `_compute_confidence_colour(r2, mape)` with `mape_to_confidence_colour(mape)` |
| PROD-03 | Direction signal suppressed and replaced with "UNCERTAIN" when forecast uncertainty band spans both positive and negative change | Fix 3: new direction logic using `ens_low`, `ens_high` vs last known price |
| PROD-04 | Interval correction applies when coverage < 0.80 (not 0.70); v3 models default to 0.60 so always corrected | Fix 4: single threshold change at line 286 of service.py |
| PROD-05 | Every forecast response includes data freshness field; UI shows visible warning when last_data_date > 30 days ago | Fix 5: new schema fields + frontend yellow banner |
</phase_requirements>

---

## Summary

Phase 7 is a surgical hardening pass on the existing forecast serving layer. All five fixes land in at most four files: `backend/app/forecast/service.py`, `backend/app/forecast/schemas.py`, `frontend/src/services/forecast.ts`, and `frontend/src/app/forecast/page.tsx`. No migrations, no new endpoints, no new dependencies.

The current `_compute_confidence_colour` function combines R² and MAPE using thresholds (R² ≥ 0.75 for Green, etc.) that are misaligned with what the meta actually stores reliably. R² is highly volatile for ag commodities over 365-day horizons (as noted in project memory: "Most commodities get negative out-of-sample R²"). The fix replaces this with a MAPE-only gate, which is what the meta reliably provides and what the project already validated in Phase 4 as the confidence metric.

The direction signal currently reads `pct = (ens_mid[-1] - ens_mid[0]) / ens_mid[0]` with no reference to the band width. A model with 40% MAPE can show "UP" with high visual authority even when the uncertainty band spans ±₹500. The fix adds a straddling check using the final-day `ens_low` and `ens_high` vs the current price before computing direction.

The `last_data_date` field is already present in the schema and is already populated by `_invoke_model()` from `meta.get("last_data_date", "2025-10-30")`. The fix converts this to a freshness computation and adds `data_freshness_days`/`is_stale` to the response, plus four farmer-readable metadata fields.

**Primary recommendation:** Implement all five fixes in a single wave — they share the same data path (meta → service → schema → frontend) and must not be split into separate plans that each pass through partially-correct states.

---

## Standard Stack

### Core (no changes needed)

| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| FastAPI | existing | HTTP routing | No new routes |
| Pydantic v2 | existing | Schema validation | Add 4 new Optional fields to ForecastResponse |
| Prophet | existing | Forecast model | Already loaded via joblib |
| pytest | existing | Backend tests | `pytest backend/tests/test_forecast_service.py` |
| Vitest | existing | Frontend tests | `npx vitest run` |

### Supporting

| Component | Purpose | Notes |
|-----------|---------|-------|
| `datetime.date.fromisoformat()` | Parse `last_data_date` string from meta | Already a string in "YYYY-MM-DD" format; `date.fromisoformat()` is built-in Python 3.7+ |
| `math.floor()` or round-to-10 | Round `typical_error_inr` to nearest ₹10 | `round(value / 10) * 10` is sufficient |

---

## Architecture Patterns

### Recommended Code Structure for Phase 7

All changes are modifications to existing files. No new files required.

```
backend/app/forecast/
├── service.py          # 5 targeted changes (gate, confidence fn, direction, interval, freshness)
├── schemas.py          # 4 new fields added to ForecastResponse
└── routes.py           # No changes needed

frontend/src/
├── services/forecast.ts          # 4 new fields added to ForecastResponse interface
└── app/forecast/page.tsx         # Stale banner, UNCERTAIN badge, hide chart on Red
```

### Pattern 1: Corrupted Model Gate (Fix 1)

**What:** Early-exit check in `get_forecast()` before the R²/tier gate that already exists.
**When to use:** Immediately after `load_meta()` returns non-None.
**Where it lands:** Lines 92–108 of `service.py` — insert before the existing R²/tier gate.

```python
# Source: CONTEXT.md Fix 1, service.py lines 91-108
def get_forecast(self, commodity, district, horizon):
    cached = self._lookup_cache(commodity, district, horizon)
    if cached is not None:
        return cached

    slug = _slugify(commodity)
    meta = load_meta(slug)

    if meta is None:
        return self._seasonal_fallback(commodity, district, horizon)

    # PROD-01: Block corrupted models before any other check
    prophet_mape = meta.get("prophet_mape")
    if prophet_mape is not None and prophet_mape > 5.0:
        return self._seasonal_fallback(commodity, district, horizon)

    # Existing tier/R² gate continues below...
```

The `_seasonal_fallback()` already sets `tier_label="seasonal_average"` and `confidence_colour="Yellow"`. The CONTEXT.md requires `confidence: "insufficient_data"` but since this is a string enum field, the planner should decide whether to add a new string value or reuse the `coverage_message` field. Research finding: the existing `coverage_message` field in `ForecastResponse` is already the correct carrier for this message.

### Pattern 2: MAPE-Only Confidence (Fix 2)

**What:** Replace the compound `_compute_confidence_colour(r2, mape)` function with a clean `mape_to_confidence_colour(mape)`.
**Why rename:** The existing test file (`test_forecast_service.py` line 114) already imports `mape_to_confidence_colour` from `app.forecast.service` — the test was written for the target state, not the current state. The function must be named `mape_to_confidence_colour` to make the existing test pass.

```python
# Source: test_forecast_service.py line 114 confirms this exact function signature
def mape_to_confidence_colour(mape: Optional[float]) -> str:
    """MAPE-based confidence: Green < 0.15, Yellow 0.15-0.35, Red > 0.35."""
    if mape is None or mape > 0.35:
        return "Red"
    if mape < 0.15:
        return "Green"
    return "Yellow"
```

The old `_compute_confidence_colour` is deleted. All call sites in `_invoke_model()` switch to `mape_to_confidence_colour(prophet_mape)`. The R²-based override block at lines 240–243 is also removed.

### Pattern 3: Direction Signal with Straddling Check (Fix 3)

**What:** After computing `ens_low` and `ens_high`, compare final-day values against the current (last known) price to determine if band straddles zero change.
**Critical detail:** The current implementation uses `ens_mid[0]` (first forecast day) as the reference price. The CONTEXT.md intent is to compare against the _current_ price (last known data point). For serving purposes, these are essentially equivalent since `ens_mid[0]` is the first forecast step. Use `ens_mid[0]` as the proxy for current price — it avoids a DB lookup and is already in-memory.

```python
# Source: service.py lines 334-337, CONTEXT.md Fix 3
# CURRENT (lines 334-337):
if len(ens_mid) >= 2 and ens_mid[0] > 0:
    pct = (ens_mid[-1] - ens_mid[0]) / ens_mid[0]
    direction = "up" if pct > 0.02 else ("down" if pct < -0.02 else "flat")

# NEW pattern:
if len(ens_mid) >= 2 and ens_mid[0] > 0:
    current_price = ens_mid[0]
    final_low = float(max(0.0, ens_low[-1]))
    final_high = float(ens_high[-1])
    pct = (ens_mid[-1] - current_price) / current_price

    if abs(pct) <= 0.02:
        direction = "flat"
    elif final_low > current_price:
        direction = "up"
    elif final_high < current_price:
        direction = "down"
    else:
        direction = "uncertain"  # band straddles zero change
```

**Important:** The `direction` field in `ForecastResponse` is typed as `str` (not a Literal), so adding "uncertain" requires no schema change. The frontend TypeScript interface currently types it as `'up' | 'down' | 'flat'` — this MUST be extended to include `'uncertain'`.

### Pattern 4: Interval Correction Threshold (Fix 4)

**What:** Single line change at `service.py` line 286.

```python
# CURRENT (line 286):
if interval_coverage < 0.70 and interval_coverage > 0:

# NEW:
if interval_coverage < 0.80 and interval_coverage > 0:
```

**v3 models default:** Current line 235 is `interval_coverage: float = meta.get("interval_coverage_80pct", 0.80) or 0.80`. For v3 models that lack this field, this returns `0.80`. The CONTEXT.md says v3 models should default to `0.60` (always apply correction). Change the default from `0.80` to `0.60`.

```python
# CURRENT (line 235):
interval_coverage: float = meta.get("interval_coverage_80pct", 0.80) or 0.80

# NEW:
interval_coverage: float = meta.get("interval_coverage_80pct", 0.60) or 0.60
```

This is two changes: the default value AND the threshold. Together they ensure v3 models (which commonly have very poor interval calibration as seen in `ajwan_meta.json` where `interval_coverage_80pct: 0.0849`) always get the correction applied.

### Pattern 5: Data Freshness Fields (Fix 5)

**Schema additions (schemas.py):**

```python
# Add to ForecastResponse after existing fields:
data_freshness_days: int = 0
is_stale: bool = False
n_markets: int = 0
typical_error_inr: Optional[float] = None
```

**Service computation (service.py, in `_invoke_model`):**

```python
# After last_data_date extraction:
from datetime import date as date_type
try:
    last_date = date_type.fromisoformat(last_data_date)
    freshness_days = (date_type.today() - last_date).days
except (ValueError, TypeError):
    freshness_days = 0

is_stale = freshness_days > 30
n_markets = len(districts_list)

# typical_error_inr: prophet_mape * current_price, rounded to nearest 10
# Use ens_mid[0] as current_price proxy (computed later in the method)
# Must be computed after ens_mid is available
```

**Timing issue:** `ens_mid` is not available until after model prediction. Compute `typical_error_inr` at the point where `forecast_points` is assembled, using `ens_mid[0]` as the current price reference:

```python
typical_error_inr = (
    round((prophet_mape * ens_mid[0]) / 10) * 10
    if prophet_mape is not None and len(ens_mid) > 0 and ens_mid[0] > 0
    else None
)
```

**Freshness in seasonal fallback and cache paths:** `_seasonal_fallback()` and `_lookup_cache()` also construct `ForecastResponse`. Both currently hardcode `last_data_date="2025-10-30"`. For the seasonal fallback, freshness can be computed the same way. For the cache path, `ForecastCache` model does not currently store freshness — options:
1. Recompute freshness at cache-read time from `last_data_date` stored in the cache row.
2. Add freshness columns to `ForecastCache` table (requires Alembic migration).

**Recommendation:** Option 1 — recompute at cache-read time. The `ForecastCache` ORM row already stores `last_data_date` as a string in the hardcoded value. Since cache is only valid 24 hours, recomputing from the stored date is fine and avoids a migration.

**Cache limitation found:** `_lookup_cache()` at line 142 hardcodes `last_data_date="2025-10-30"` — this field is not stored in the `ForecastCache` table. The new fields (`data_freshness_days`, `is_stale`, etc.) cannot be populated from cache without either: (a) adding columns to `forecast_cache` table, or (b) re-deriving from the commodity meta at cache-read time.

**Recommended approach:** On cache hit, call `load_meta(slug)` to get the current `last_data_date`, compute freshness from it, and populate the new fields. This is a small extra JSON read (not model load) and avoids a migration.

### Anti-Patterns to Avoid

- **Anti-pattern — splitting the gate into pre-processing scripts:** All 14 corrupted models must be blocked at serve time, not at training time. If a new corrupted model is deployed, it must be automatically blocked.
- **Anti-pattern — using `r2_score` as the primary confidence signal:** R² is negative for most ag commodity models. Using it as the primary gate (as the current code does with the `r2 < 0.5 → Red` override) produces misleading results because good-MAPE models get downgraded by bad R².
- **Anti-pattern — relying on cache for freshness metadata:** Cache rows don't carry all new fields. Either compute from meta at cache-hit time, or the response will have stale/wrong freshness values.
- **Anti-pattern — changing `direction` to a Literal type in Pydantic:** The field is used as a plain string throughout. Pydantic will coerce/validate. Keep it as `str` in the Python schema and add `'uncertain'` to the TypeScript union type.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MAPE threshold logic | Custom multi-condition confidence engine | Simple 3-case if/elif using prophet_mape | Already sufficient; project memory confirms prophet_mape is the reliable metric |
| Date parsing | Custom regex or strptime format guessing | `date.fromisoformat(last_data_date)` | Meta stores ISO format ("2025-10-30"); built-in handles it cleanly |
| Direction uncertainty | Statistical hypothesis test | Band-vs-current comparison with `ens_low`/`ens_high` | Sufficient for farmer use case; avoids complexity |
| Rounding to ₹10 | Custom rounding library | `round(value / 10) * 10` | Standard Python; no dependency needed |

---

## Common Pitfalls

### Pitfall 1: v3 Meta Missing Fields
**What goes wrong:** `tomato_meta.json` (v3 format) has only: `alpha`, `r2_score`, `prophet_mape`, `xgb_mape`, `last_data_date`, `districts_list`, `trained_at`. It is missing `tier`, `strategy`, `interval_coverage_80pct`, `n_districts`, `exog_columns`, `commodity_category`.
**Why it happens:** v3 was trained before v4 added these fields.
**How to avoid:** Always use `.get(key, default)` with appropriate defaults for all meta fields. Specifically: `interval_coverage_80pct` default must be `0.60` (not `0.80`) after Fix 4.
**Warning signs:** `KeyError` on meta dict access = missing `.get()`.

### Pitfall 2: Existing Test Expects `mape_to_confidence_colour` Name
**What goes wrong:** `backend/tests/test_forecast_service.py` line 114 imports `mape_to_confidence_colour` from `app.forecast.service`. The current code has `_compute_confidence_colour`. If the rename is missed, the test fails with ImportError.
**Why it happens:** The test was written for the target state (phase 7), not the current state.
**How to avoid:** Rename `_compute_confidence_colour` → `mape_to_confidence_colour` and make it a module-level public function (no underscore). Remove the old private function entirely.
**Warning signs:** `ImportError: cannot import name 'mape_to_confidence_colour'`.

### Pitfall 3: Cache Bypasses New Fields
**What goes wrong:** When a forecast is served from `forecast_cache`, the response is constructed at line 132 using only columns stored in the DB. The four new fields (`data_freshness_days`, `is_stale`, `n_markets`, `typical_error_inr`) are not in the cache table.
**Why it happens:** `ForecastCache` ORM model pre-dates Phase 7 fields.
**How to avoid:** After a cache hit, call `load_meta(_slugify(commodity))` and compute freshness/n_markets fields before returning the ForecastResponse. Add `data_freshness_days`, `is_stale`, `n_markets`, `typical_error_inr` to the response constructed in `_lookup_cache()`.
**Warning signs:** Frontend shows `data_freshness_days: 0` and `is_stale: false` for all cached responses.

### Pitfall 4: `typical_error_inr` Available Before `ens_mid`
**What goes wrong:** `typical_error_inr` needs `ens_mid[0]` as a price proxy, but `ens_mid` is computed mid-way through `_invoke_model()`. If `typical_error_inr` is computed at the top of the method, `ens_mid` doesn't exist yet.
**Why it happens:** Method flow: extract meta → predict → combine → compute direction → build response.
**How to avoid:** Compute `typical_error_inr` in the response-building block at lines 342–365, after `ens_mid` is sliced to the requested horizon.

### Pitfall 5: `direction = "uncertain"` Not in TypeScript Union
**What goes wrong:** `forecast.ts` types `direction` as `'up' | 'down' | 'flat'`. When backend returns `"uncertain"`, TypeScript infers a type error, and `DIRECTION_CONFIG["uncertain"]` is `undefined` in the page component (line 100).
**Why it happens:** TypeScript union type was defined before "uncertain" existed.
**How to avoid:**
1. Add `'uncertain'` to the union in `forecast.ts`.
2. Add an `uncertain` entry to `DIRECTION_CONFIG` in `page.tsx` with a grey neutral badge.
3. Ensure `dirConfig` fallback handles null gracefully (it does: `const dirConfig = forecast ? DIRECTION_CONFIG[forecast.direction] : null`).

### Pitfall 6: Chart Shown for Red-Badge Responses
**What goes wrong:** The CONTEXT.md is explicit: "Do NOT show a chart with a Red badge. Remove the chart entirely for Red/insufficient." The current page.tsx renders the chart whenever `forecast.forecast_points && forecast.forecast_points.length > 0` — regardless of confidence.
**Why it happens:** Current page has no confidence-based chart suppression.
**How to avoid:** Wrap the chart render block with an additional condition: `&& forecast.confidence_colour !== "Red"`.

### Pitfall 7: `_seasonal_fallback` Sets `confidence_colour = "Yellow"` — Should It Change?
**What goes wrong:** After Fix 1, corrupted models route to `_seasonal_fallback()`, which returns `confidence_colour: "Yellow"`. The CONTEXT.md says corrupted models should return `"confidence": "insufficient_data"`. But the schema field is `confidence_colour` with values "Green"/"Yellow"/"Red".
**Why it happens:** The CONTEXT.md uses shorthand "insufficient_data" as a concept, not as a literal field value.
**How to avoid:** Use the existing `coverage_message` field to carry the "Insufficient data for [commodity] in [district]" message. Set `confidence_colour: "Red"` (not Yellow) for the corrupted model path. Override in `_seasonal_fallback` or create a dedicated path for corrupted models.

**Recommended resolution:** Add a `reason` parameter to `_seasonal_fallback()` (default `None`). When called from the corrupted-model gate, pass `reason="corrupted"` which sets `confidence_colour="Red"` and appropriate `coverage_message`.

---

## Code Examples

### Full Direction Logic Replacement
```python
# Source: service.py lines 333-338, replacing with Fix 3 logic
# Place this block after ens_mid/ens_low/ens_high are sliced to horizon

if len(ens_mid) >= 2 and ens_mid[0] > 0:
    current_price = ens_mid[0]
    final_low = float(max(0.0, ens_low[-1]))
    final_high = float(ens_high[-1])
    pct = (ens_mid[-1] - current_price) / current_price

    if abs(pct) <= 0.02:
        direction = "flat"
    elif final_low > current_price:
        direction = "up"
    elif final_high < current_price:
        direction = "down"
    else:
        direction = "uncertain"
else:
    direction = "flat"
```

### New Schema Fields
```python
# Source: schemas.py ForecastResponse — add after r2_score field
data_freshness_days: int = 0
is_stale: bool = False
n_markets: int = 0
typical_error_inr: Optional[float] = None
```

### TypeScript Interface Extension
```typescript
// Source: forecast.ts ForecastResponse interface — extend existing
export interface ForecastResponse {
    // ... existing fields ...
    direction: 'up' | 'down' | 'flat' | 'uncertain';  // add 'uncertain'
    data_freshness_days: number;
    is_stale: boolean;
    n_markets: number;
    typical_error_inr: number | null;
}
```

### UNCERTAIN Direction Badge in page.tsx
```typescript
// Source: page.tsx DIRECTION_CONFIG — add uncertain case
const DIRECTION_CONFIG = {
    up: { label: "Rising", icon: TrendingUp, className: "bg-emerald-100 text-emerald-800 ..." },
    down: { label: "Falling", icon: TrendingDown, className: "bg-red-100 text-red-800 ..." },
    flat: { label: "Stable", icon: ArrowRight, className: "bg-slate-100 text-slate-800 ..." },
    uncertain: { label: "Uncertain", icon: ArrowRight, className: "bg-slate-100 text-slate-600 dark:bg-slate-800/30 dark:text-slate-400" },
}
```

### Stale Data Banner (page.tsx)
```tsx
{/* Source: CONTEXT.md Fix 5 — above the forecast chart, below the badges */}
{forecast.is_stale && (
    <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800" id="stale-data-banner">
        <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-amber-700 dark:text-amber-400">
            Price data last updated {forecast.data_freshness_days} days ago — forecast may not reflect current market conditions
        </p>
    </div>
)}
```

### Farmer Metadata Footer (page.tsx)
```tsx
{/* Source: CONTEXT.md Fix 5 extension — below the chart */}
{(forecast.n_markets > 0 || forecast.typical_error_inr != null) && (
    <p className="text-xs text-muted-foreground/70">
        Based on data from {forecast.n_markets} markets.
        {forecast.typical_error_inr != null &&
            ` Typical forecast error: ₹${forecast.typical_error_inr}/quintal.`}
    </p>
)}
```

---

## State of the Art

| Old Approach | Current Approach | Change Required | Impact |
|--------------|------------------|-----------------|--------|
| `_compute_confidence_colour(r2, mape)` — R² primary | `mape_to_confidence_colour(mape)` — MAPE only | Rename + simplify function | Aligns confidence with the metric that actually works for ag commodities |
| `interval_coverage < 0.70` threshold | `interval_coverage < 0.80` | Single line change | More models get corrected intervals, more honest display |
| v3 default `interval_coverage = 0.80` | v3 default `interval_coverage = 0.60` | Change default value | v3 models (many with 0.08 actual coverage) always corrected |
| Direction always UP/DOWN/FLAT | Direction includes UNCERTAIN | New branch in direction logic | Farmers see honest signal when model is unsure |
| `last_data_date` shown as static text | `is_stale` boolean + banner | New fields + UI component | Farmers know when data is old |

---

## Open Questions

1. **Should `_lookup_cache()` call `load_meta()` for freshness?**
   - What we know: Cache rows don't store freshness. `load_meta()` is a JSON file read (cheap, not model load).
   - What's unclear: Whether the added file read on every cache hit is acceptable (it is cheap but adds I/O).
   - Recommendation: Yes — call `load_meta()` on cache hit to populate freshness fields. The meta JSON is ~2KB, and cachetools LRU does not cache meta separately, but it's fast enough for this use case.

2. **`confidence_colour: "Red"` vs `"insufficient_data"` for corrupted models**
   - What we know: Schema uses "Green"/"Yellow"/"Red" as string values. CONTEXT.md uses "insufficient_data" as a concept.
   - What's unclear: Whether "insufficient_data" should be a new valid confidence_colour value or if "Red" covers it.
   - Recommendation: Use `"Red"` as the colour value (consistent with schema) and use `coverage_message` to carry the "Insufficient data" text. This avoids a frontend CONFIDENCE_CONFIG addition for a rarely-triggered case.

3. **`tier_label` value for corrupted model path**
   - What we know: CONTEXT.md says `"tier": "seasonal_average"`. The existing `_seasonal_fallback` sets `tier_label="seasonal_average"`.
   - What's unclear: Whether to use `"seasonal_average"` or `"insufficient_data"` as the tier_label for corrupted models.
   - Recommendation: Use `tier_label="seasonal_average"` (existing value, no frontend change needed). The `coverage_message` distinguishes it as corrupted.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), Vitest (frontend) |
| Config file | `backend/pytest.ini`, `frontend/vitest.config.ts` |
| Quick run command (backend) | `cd backend && python -m pytest tests/test_forecast_service.py tests/test_forecast_api.py -x -v` |
| Quick run command (frontend) | `cd frontend && npx vitest run src/app/forecast` |
| Full suite command | `cd backend && python -m pytest -x -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROD-01 | `prophet_mape > 5.0` routes to seasonal fallback | unit | `pytest tests/test_forecast_service.py::test_corrupted_model_blocked -x` | ❌ Wave 0 |
| PROD-02 | `mape_to_confidence_colour(0.05)` returns "Green", `(0.20)` returns "Yellow", `(0.40)` returns "Red" | unit | `pytest tests/test_forecast_service.py::test_confidence_colour_mapping -x` | ✅ exists (line 111) |
| PROD-02 | Existing test passes with renamed function | unit | `pytest tests/test_forecast_service.py -x` | ✅ exists |
| PROD-03 | `direction = "uncertain"` when band straddles zero | unit | `pytest tests/test_forecast_service.py::test_direction_uncertain_when_band_straddles -x` | ❌ Wave 0 |
| PROD-03 | `direction = "up"` only when `final_low > current_price` | unit | `pytest tests/test_forecast_service.py::test_direction_up_only_when_band_above -x` | ❌ Wave 0 |
| PROD-04 | v3 meta (no `interval_coverage_80pct`) defaults to 0.60, correction applied | unit | `pytest tests/test_forecast_service.py::test_interval_correction_v3_default -x` | ❌ Wave 0 |
| PROD-05 | `data_freshness_days` computed correctly from `last_data_date` | unit | `pytest tests/test_forecast_service.py::test_data_freshness_fields -x` | ❌ Wave 0 |
| PROD-05 | `is_stale = True` when freshness > 30 days | unit | `pytest tests/test_forecast_service.py::test_is_stale_threshold -x` | ❌ Wave 0 |
| PROD-05 | `is_stale` banner renders in frontend when `is_stale=true` | unit (Vitest) | `cd frontend && npx vitest run src/app/forecast` | ❌ Wave 0 |
| PROD-05 | `ForecastResponse` schema includes new fields | unit | `pytest tests/test_forecast_service.py::test_response_schema_fields -x` | ✅ exists (extend) |
| (chart gate) | Chart hidden when `confidence_colour = "Red"` | unit (Vitest) | `cd frontend && npx vitest run src/app/forecast` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && python -m pytest tests/test_forecast_service.py tests/test_forecast_api.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest -x -q && cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

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

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `backend/app/forecast/service.py` — current implementation including interval correction at 0.70, direction logic, `_compute_confidence_colour`
- Direct code inspection: `backend/app/forecast/schemas.py` — current ForecastResponse fields
- Direct code inspection: `backend/app/ml/loader.py` — `load_meta()`, `_resolve_artifact()`, v3/v4 fallback logic
- Direct code inspection: `ml/artifacts/tomato_meta.json` — confirmed v3 meta structure (missing tier, interval_coverage, n_districts)
- Direct code inspection: `ml/artifacts/v4/ajwan_meta.json` — confirmed v4 meta structure including `interval_coverage_80pct: 0.0849` (extreme miscalibration example)
- Direct code inspection: `frontend/src/services/forecast.ts` — TypeScript interface, direction union type
- Direct code inspection: `frontend/src/app/forecast/page.tsx` — DIRECTION_CONFIG, CONFIDENCE_CONFIG, chart render conditions
- Direct code inspection: `backend/tests/test_forecast_service.py` — confirmed `mape_to_confidence_colour` import on line 114 (test expects the target state)

### Secondary (MEDIUM confidence)

- Project MEMORY.md: "Confidence color: uses `prophet_mape` from meta (in-sample, reliable). NOT out-of-sample R² (too volatile for ag commodities)" — confirms MAPE-only approach
- Project MEMORY.md: "R² badge: only shown in UI when `r2_score > 0`. Most commodities get negative out-of-sample R² (expected for 365-day ag forecasts)" — confirms R² should not gate confidence

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all existing infrastructure
- Architecture: HIGH — all changes are in identified files at identified lines
- Pitfalls: HIGH — discovered through direct code inspection, not speculation
- Test gaps: HIGH — specific test names and behaviors identified

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable codebase, no external API dependencies)
