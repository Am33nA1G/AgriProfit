# Design: Transport Calculator — Full Price Breakdown & Best Option Explanation

**Date:** 2026-02-28
**Scope:** Frontend only — backend already returns all required fields

---

## Problem

The transport calculator frontend is wired to the old API schema. The logistics engine
(merged 2026-02-28) returns rich data — verdict, stress test, spoilage, risk scores,
full cost line items — none of which reaches the user. The "why it's the best" section
is fabricated from simple math rather than the engine's actual reasoning.

## Solution

Expand the best mandi card into a 4-tab layout. The comparison table below is unchanged.

---

## Changes Required

### 1. `frontend/src/services/transport.ts`
Update `MandiComparison` and `CostBreakdown` interfaces to include all new fields:

**CostBreakdown additions:**
- `driver_bata`, `cleaner_bata`, `halt_cost`, `breakdown_reserve`
- `permit_cost`, `rto_buffer`, `loading_hamali`, `unloading_hamali`

**MandiComparison additions:**
- `verdict`, `verdict_reason`
- `travel_time_hours`, `route_type`, `is_interstate`, `diesel_price_used`
- `spoilage_percent`, `weight_loss_percent`, `grade_discount_percent`, `net_saleable_quantity_kg`
- `price_volatility_7d`, `price_trend`
- `risk_score`, `confidence_score`, `stability_class`
- `stress_test: StressTestResult | null`
- `economic_warning: string | null`

New interface:
```ts
interface StressTestResult {
  worst_case_profit: number
  break_even_price_per_kg: number
  margin_of_safety_pct: number
  verdict_survives_stress: boolean
}
```

### 2. `frontend/src/app/transport/page.tsx`
- Update the mapping block to pass all new fields through (no longer drop them)
- Replace the best mandi card with the tabbed layout described below
- Add verdict badge to each row in the comparison table

---

## Best Mandi Card Layout (4 Tabs)

### Tab 1 — Overview
- Header: mandi name + `verdict` badge (Excellent=green / Good=blue / Marginal=amber / Not Viable=red)
- `verdict_reason` as a callout paragraph (engine text, not fabricated)
- 3 stat chips: Net Profit `₹X`, Profit/kg `₹X`, ROI `X%`
- `economic_warning` amber banner (rendered only when present)
- Route line: `{distance_km} km · {travel_time_hours}h round-trip · {vehicle_type} · {trips_required} trip(s)` + interstate badge if `is_interstate`

### Tab 2 — Cost Breakdown
Waterfall list from gross revenue down to net profit:

```
Gross Revenue           ₹X
  − Spoilage/Grade loss ₹X   ← (gross × spoilage+grade factors)
Adjusted Revenue        ₹X
  − Freight             ₹X
  − Toll                ₹X
  − Driver Bata         ₹X
  − Cleaner Bata        ₹X   (0 for tempo, hidden when 0)
  − Night Halt          ₹X   (hidden when 0)
  − Breakdown Reserve   ₹X
  − Interstate Permit   ₹X   (hidden when 0)
  − RTO Buffer          ₹X
  − Loading Hamali      ₹X
  − Unloading Hamali    ₹X
  − Mandi Fee           ₹X
  − Commission          ₹X
  − Misc (weighbridge)  ₹X
─────────────────────────────
Net Profit              ₹X   (bold, green or red)
```

Zero-value rows are hidden to avoid noise.

### Tab 3 — Risk & Data
- Confidence score: labelled progress bar 0–100
- Price trend chip: Rising ↑ (green) / Falling ↓ (red) / Stable → (grey) + `{price_volatility_7d}% 7-day volatility`
- Stability class badge: Stable / Moderate / Volatile
- Stress test box (grey bg):
  - Worst-case profit: `₹X`
  - Break-even price: `₹X/kg`
  - Margin of safety: `X%`
  - Survives stress: ✓ Pass / ✗ Fail

### Tab 4 — Spoilage
- Spoilage loss: `X%`
- Weight shrinkage: `X%`
- Grade discount: `X%`
- Net saleable: `X kg of Y kg` original
- Footer note: `Diesel used: ₹{diesel_price_used}/L`

---

## Comparison Table
Unchanged except: add a `Verdict` badge column between `Vehicle` and `Net Profit`.

---

## Out of Scope
- No changes to backend
- No changes to the comparison table cost details
- No new state management
- Mobile app not affected
