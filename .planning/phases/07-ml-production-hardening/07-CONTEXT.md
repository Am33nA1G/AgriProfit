# Phase 7: ML Production Hardening - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the forecast serving layer trustworthy for real farmers before production deployment.
No retraining, no new features. Five targeted backend + frontend fixes only:
1. Block corrupted models from reaching farmers
2. Tie confidence badges to actual MAPE thresholds
3. Suppress direction signal when the model is genuinely uncertain
4. Widen prediction intervals to their stated confidence level
5. Warn when price data is stale

</domain>

<decisions>
## Implementation Decisions

### Corrupted model blocking (Fix 1)
- Hard gate: if `prophet_mape > 5.0` in meta, the model is corrupted — never serve it
- Redirect silently to seasonal fallback (already exists in service.py)
- Response label: `"tier": "seasonal_average"` + `"confidence": "insufficient_data"`
- Do NOT show any forecast chart or direction signal for these
- 14 known corrupted v3 models; the gate must apply at serve time, not offline

### Confidence badge thresholds (Fix 2)
- Current system uses arbitrary/unclear thresholds — replace entirely
- New thresholds tied to actual out-of-sample prophet_mape from meta:
  - **Green**: prophet_mape < 0.15 — model is reliable
  - **Yellow**: prophet_mape 0.15–0.35 — directional signal only, not a trading price
  - **Red / Insufficient**: prophet_mape > 0.35 OR corrupted (>5.0) — do not show forecast
- For Red: show "Insufficient data for [commodity] in [district] — seasonal pattern only"
- Do NOT show a chart with a Red badge. Remove the chart entirely for Red/insufficient.
- Frontend badge label changes: Green="Reliable", Yellow="Directional only", Red not shown (replaced by message)

### Direction signal suppression (Fix 3)
- Current: always shows UP/DOWN/FLAT regardless of uncertainty
- New rule: only show UP or DOWN if the forecast uncertainty band does NOT straddle zero change
  - i.e., if `low_forecast > current_price` → UP is valid
  - if `high_forecast < current_price` → DOWN is valid
  - if band spans both sides → direction = "UNCERTAIN"
- "UNCERTAIN" renders as a neutral grey label, not a coloured arrow
- FLAT remains: when mid forecast within ±2% of current price
- This logic lives in `service.py` before returning ForecastResponse — not in the frontend

### Interval correction threshold (Fix 4)
- Current threshold in `service.py`: apply correction if `interval_coverage < 0.70`
- Change to: apply correction if `interval_coverage < 0.80`
- Correction formula stays the same: `correction = 0.80 / interval_coverage`
- For v3 models (no interval_coverage in meta): assume 0.60 → always apply correction
- This widens bands for more models, making the displayed range more honest

### Stale data warning (Fix 5)
- Compute `data_freshness_days = (today - last_data_date).days` at serve time
- Add `data_freshness_days: int` and `is_stale: bool` to ForecastResponse schema
- Stale threshold: `is_stale = data_freshness_days > 30`
- Backend always returns these fields — frontend decides how to render
- Frontend: if `is_stale`, show a yellow banner ABOVE the forecast chart:
  "Price data last updated [N] days ago — forecast may not reflect current market conditions"
- Stale warning does NOT suppress the forecast — it accompanies it
- Data freshness must be shown even for Green-badge models

### Farmer-readable metadata (Fix 5 extension)
- Add to ForecastResponse: `n_markets: int` (len(districts_list) from meta)
- Add to ForecastResponse: `typical_error_inr: float` (prophet_mape × current_price, rounded to nearest ₹10)
- Frontend shows below the chart: "Based on data from {n_markets} markets. Typical forecast error: ₹{typical_error_inr}/quintal."
- This replaces the raw MAPE number — farmers understand rupees, not percentages

### What NOT to change
- Do not retrain any models
- Do not change the forecast API endpoint URL or request parameters
- Do not change the nightly scheduler
- Do not add new endpoints — extend existing ForecastResponse schema only
- Do not touch the seasonal calendar, soil advisor, or arbitrage pages

</decisions>

<specifics>
## Specific Ideas

- The user's stated principle: "I don't want to provide lies. I want to give farmers information they can trust and rely on."
- A farmer trucking produce 200km on a wrong UP signal loses real money — wrong forecasts cause direct harm
- "Insufficient data" shown honestly is better than a confident-looking wrong forecast
- Farmers understand rupees (₹), not MAPE percentages — always translate model error into ₹ terms
- The Green badge should feel like a certification, not decoration — only earn it at MAPE < 0.15
- The direction signal UNCERTAIN should feel neutral and honest, not like a failure

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/forecast/service.py:286-291` — interval correction already implemented at 0.70 threshold; change to 0.80
- `backend/app/ml/loader.py:load_meta()` — returns full meta dict including prophet_mape, last_data_date, districts_list, interval_coverage_80pct
- `backend/app/forecast/schemas.py` — ForecastResponse already has confidence, tier, direction fields; extend it
- Seasonal fallback path already exists in service.py — corrupted models route there without new code

### Established Patterns
- ForecastResponse is the single schema returned by `/api/v1/forecast/{commodity}/{district}`
- Confidence color is computed in service.py from meta, passed to frontend as a string field
- Frontend reads `confidence` and `direction` strings — changing their values requires frontend rendering changes
- v4 metas have `interval_coverage_80pct`; v3 metas do not — default v3 to 0.60 for correction

### Integration Points
- `backend/app/forecast/service.py` — all 5 fixes land here (gate, thresholds, direction logic, interval, staleness)
- `backend/app/forecast/schemas.py` — add `data_freshness_days`, `is_stale`, `n_markets`, `typical_error_inr`
- `frontend/src/app/forecast/page.tsx` — render stale banner, UNCERTAIN badge, remove chart for Red/insufficient
- `frontend/src/services/forecast.ts` — add new fields to TypeScript interface

</code_context>

<deferred>
## Deferred Ideas

- Full v4 retraining for all 256 commodities — Phase 8
- Walk-forward backtesting to validate direction accuracy — Phase 8
- Conformal prediction for properly calibrated intervals — Phase 8
- "Beat the naive baseline" gate before promoting to full model — Phase 8
- Farmer-facing explanation of why a forecast is low confidence — future UX phase

</deferred>

---

*Phase: 07-ml-production-hardening*
*Context gathered: 2026-03-08*
