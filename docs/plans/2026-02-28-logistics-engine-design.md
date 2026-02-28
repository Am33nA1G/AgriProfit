# Real-World Agricultural Logistics Decision Engine — Design Doc
**Date:** 2026-02-28
**Status:** Approved
**Replaces:** Basic transport cost calculator in `service.py`

---

## Goal

Upgrade the existing transport comparison module into a real-world agricultural logistics decision engine that:
- Models Indian mandi transport economics faithfully (driver bata, diesel sensitivity, interstate regulations)
- Quantifies perishability risk using exponential spoilage decay
- Scores price credibility using 7-day rolling volatility
- Produces a composite risk score with stress testing
- Applies behavioral corrections matching farmer decision patterns
- Flags economic anomalies with guardrails
- Produces structured JSON audit logs per comparison

---

## Architecture: Approach B — Dedicated Sub-modules

```
backend/app/transport/
├── routing.py           [UNCHANGED] — OSRM + DB cache + haversine fallback
├── district_coords.json [UNCHANGED] — 858 district coordinates
├── economics.py         [NEW] — freight, diesel sensitivity, bata, permit, breakdown reserve
├── spoilage.py          [NEW] — perishability decay, weight loss, grade discount, hamali
├── price_analytics.py   [NEW] — 7-day volatility, price trend, confidence scoring
├── risk_engine.py       [NEW] — risk composite, stress test, behavioral scoring, guardrails
├── service.py           [MODIFIED] — orchestrator; integrates all new modules
├── schemas.py           [MODIFIED] — ~25 new output fields
└── routes.py            [MINOR] — expose new fields in /compare and /calculate
```

**Config additions** (`backend/app/core/config.py`):
```python
diesel_price_per_liter: float = 98.0      # ₹/L, overrideable via .env
diesel_baseline_price: float = 98.0       # baseline for sensitivity calc
transport_weather_risk_weight: float = 0.3  # placeholder weather risk (0–1)
transport_max_mandis_evaluated: int = 25   # hard cap before pre-filter
```

---

## Module 1: `economics.py` — Real Indian Freight Model

### Constants (2026 production-ready, user-approved)

```python
BATA = {
    "TEMPO":       {"driver_day": 950,  "cleaner_day": 0,   "night_halt": 900},
    "TRUCK_SMALL": {"driver_day": 1200, "cleaner_day": 650, "night_halt": 1100},
    "TRUCK_LARGE": {"driver_day": 1500, "cleaner_day": 850, "night_halt": 1400},
}
BREAKDOWN_RESERVE_PER_KM = 1.0    # ₹ per km, both ways
RTO_FRICTION_INTRASTATE  = 0.015  # 1.5% of raw freight
RTO_FRICTION_INTERSTATE  = 0.025  # 2.5% of raw freight
INTERSTATE_PERMIT_COST   = 1200.0 # ₹ flat
DIESEL_DEPENDENCY = {
    "TEMPO":       0.55,
    "TRUCK_SMALL": 0.62,
    "TRUCK_LARGE": 0.68,
}
PRACTICAL_CAPACITY_FACTOR = 0.90  # 90% utilization cap
TOLL_PLAZA_SPACING_KM     = 70    # heuristic (real NHAI avg: 65–75 km)
WORKING_HOURS_PER_DAY     = 10    # for days = ceil(round_trip_h / 10)
```

### Travel Speed by Route Type
```python
HILL_STATES = {
    "jammu and kashmir", "himachal pradesh", "uttarakhand", "sikkim",
    "arunachal pradesh", "meghalaya", "nagaland", "manipur", "mizoram",
    "tripura",
}
SPEED_KMH = {
    "highway": 55,  # National Highway, no significant hills
    "mixed":   42,  # State/district roads
    "hill":    32,  # Hill state routing
}
URBAN_CONGESTION_FACTOR = 1.15  # +15% to travel time
```

Speed selection logic: if source OR destination state is a hill state → 32 km/h.
Urban congestion applied when source or destination is a state capital.

### Freight Formula (step-by-step)

```
effective_rate = base_rate × (1 + diesel_dependency × ((diesel_price - baseline) / baseline))
practical_capacity = vehicle_capacity × 0.90
trips = ceil(quantity_kg / practical_capacity)
raw_transport = distance_km × effective_rate × 2 × trips
toll_plazas = max(0, round(distance_km / 70))
toll_cost = toll_plazas × toll_per_plaza × 2 × trips
round_trip_hours = (distance_km / avg_speed) × 2
days = max(1, ceil(round_trip_hours / 10))
bata_total = (driver_day + cleaner_day) × days
halt_cost = night_halt if round_trip_hours > 12 else 0
breakdown_reserve = BREAKDOWN_RESERVE_PER_KM × distance_km × 2
permit_cost = 1200.0 if source_state != mandi_state else 0
rto_buffer = raw_transport × (0.025 if interstate else 0.015)
total_freight = raw_transport + toll_cost + bata_total + halt_cost
              + breakdown_reserve + permit_cost + rto_buffer
```

### Validated Worked Example
- truck_small, 292 km intrastate, 5500 kg, diesel ₹98, 42 km/h
- Result: **₹23,581 total freight (~₹4.29/kg)** — verified realistic for 2026

---

## Module 2: `spoilage.py` — Perishability & Market Loss

### Spoilage Rates (per 24h, open-truck, ambient temperature)

| Category | Rate/24h | Weight Loss % | Grade Discount % |
|----------|----------|---------------|-----------------|
| Vegetable | 3.0% | 2.5% | 4.0% |
| Fruit | 5.0% | 2.0% | 5.0% |
| Spice | 0.3% | 0.5% | 1.0% |
| Grain/Paddy | 0.15% | 0.75% | 0.5% |
| Pulses | 0.10% | 0.50% | 0.5% |
| Unknown (NULL) | 0.50% | 0.75% | 1.0% |

### Exponential Decay Formula (user-approved)

```python
spoilage_fraction = 1 - (1 - rate_per_24h) ** (round_trip_hours / 24)
```

Rationale: spoilage is a hazard process; exponential decay gives physically correct behaviour at sub-24h and multi-day trips.

### Quick Reference Table (% quantity lost)

| Category | 12h | 24h | 36h | 48h |
|----------|-----|-----|-----|-----|
| Vegetable (3%) | 1.51% | 3.00% | 4.47% | 5.91% |
| Fruit (5%) | 2.53% | 5.00% | 7.41% | 9.75% |
| Grain (0.15%) | 0.075% | 0.15% | 0.225% | 0.30% |

### Auction Underbidding Risk
If price volatility > 8%: grade_discount += 1.5pp

### Net Revenue Formula
```python
net_quantity = quantity_kg × (1 - spoilage_fraction) × (1 - weight_loss_fraction)
net_revenue  = net_quantity × price_per_kg × (1 - grade_discount_fraction)
```

### Regional Hamali Rates (₹/quintal)

| Region | Loading | Unloading |
|--------|---------|-----------|
| North (UP, Punjab, Haryana, Bihar, MP) | ₹10 | ₹12 |
| South (Kerala, TN, Karnataka, AP, TG) | ₹18 | ₹22 |
| Maharashtra / Gujarat | ₹13 | ₹16 |
| Default / Unknown | ₹15 | ₹18 |

---

## Module 3: `price_analytics.py` — Price Credibility

### Query (date-bounded, safe on 25M-row price_history)
```sql
SELECT modal_price, price_date FROM price_history
WHERE commodity_id = :cid
  AND mandi_name = :name
  AND price_date >= :max_date - INTERVAL '7 days'
ORDER BY price_date DESC
LIMIT 7
```

### Outputs

```python
volatility_pct  = stddev(prices) / mean(prices) * 100  # coefficient of variation
price_trend     = "rising" | "falling" | "stable"
  # rising:  latest > mean * 1.03
  # falling: latest < mean * 0.97
  # stable:  else
confidence_score = 100
  - 20  if volatility_pct > 8%
  - 15  if days_since_last_price > 3
  - 25  if n_records == 1  (thin/inactive mandi)
confidence_score = max(10, confidence_score)  # floor at 10
```

---

## Module 4: `risk_engine.py` — Risk, Stress, Behavioral, Guardrails

### Composite Risk Score (0–100)
```python
risk_score = (
    min(1.0, volatility_pct / 20.0)  * 0.25  # price volatility
  + min(1.0, distance_km / 1000.0)   * 0.20  # distance risk
  + min(1.0, spoilage_fraction / 0.15) * 0.20 # spoilage risk
  + min(1.0, abs(diesel_delta) / 0.20) * 0.15 # fuel sensitivity
  + (1.0 if is_interstate else 0.0)  * 0.10  # regulatory risk
  + weather_risk_weight               * 0.10  # placeholder (config: 0.3)
) * 100
```

**stability_class:**
- `stable`:   risk_score < 30
- `moderate`: 30 ≤ risk_score < 60
- `volatile`: risk_score ≥ 60

### Stress Test Simulation (all shocks applied simultaneously)
| Parameter | Shock |
|-----------|-------|
| Diesel price | +15% |
| Toll cost | +25% |
| Mandi price | −12% |
| Spoilage fraction | +5pp absolute |
| Grade discount | +3pp absolute |

```python
worst_case_profit    = recompute net_profit with all stress params
break_even_price_kg  = total_stressed_cost / net_quantity_stressed
margin_of_safety_pct = (normal_profit - worst_case_profit) / max(abs(normal_profit), 1) * 100
# If worst_case_profit < 0: downgrade verdict by 1 tier
```

### Behavioral Scoring (verdict downgrade logic)
Applied after all economic calculations, before final verdict assignment:

| Condition | Action |
|-----------|--------|
| distance_km > 700 | Downgrade verdict 1 tier |
| profit_diff vs nearest mandi < 5% | Prefer closer (downgrade far mandi, add note) |
| risk_score > 70 | Downgrade verdict 1 tier |
| Multiple conditions | Cap total downgrade at 2 tiers |

Verdict tier order: `excellent → good → marginal → not_viable`

### Economic Guardrails (economic_warning field)
| Condition | Warning |
|-----------|---------|
| ROI > 500% | "ROI anomaly — verify price data and commodity" |
| net_margin > 55% | "Margin anomaly — check mandi fees and distance" |
| total_cost < 6% of gross | "Cost unusually low — estimated distance may underestimate actual" |
| profit_per_kg > price_per_kg × 0.8 | "Profit exceeds 80% of price — data integrity check needed" |

---

## Modified: `service.py` — Updated Orchestrator

**New `compare_mandis()` flow:**
1. Resolve commodity → ID (unchanged)
2. `get_mandis_for_commodity()` → raw mandis with price (unchanged)
3. Pull 7-day price analytics per mandi via `price_analytics.py`
4. Resolve source coords (unchanged)
5. Pre-filter top 25 candidates by price descending (cap to `transport_max_mandis_evaluated`)
6. Parallel OSRM distance fetch (unchanged ThreadPoolExecutor)
7. Compute travel time + speed selection via `economics.py`
8. Compute freight breakdown (all 12 components) via `economics.py`
9. Compute spoilage and hamali via `spoilage.py`
10. Compute risk score + stress test via `risk_engine.py`
11. Apply behavioral scoring via `risk_engine.py`
12. Check guardrails via `risk_engine.py`
13. Sort by net_profit, assign verdicts, enforce performance cap (max 25 results)
14. Emit structured audit log per mandi
15. Return `TransportCompareResponse`

**Audit log format (structured JSON, logged via `logging.getLogger("transport.audit")`):**
```json
{
  "event": "transport_comparison",
  "mandi_id": "<uuid>",
  "price_date": "YYYY-MM-DD",
  "distance_source": "osrm|estimated",
  "diesel_price": 98.0,
  "spoilage_pct": 3.0,
  "volatility_pct": 5.2,
  "stress_test_worst_case": -1240.0,
  "risk_score": 42.5,
  "verdict": "marginal",
  "travel_time_hours": 13.9,
  "is_interstate": false
}
```

---

## Modified: `schemas.py` — New Output Fields

### `CostBreakdown` additions
```python
driver_bata: float        # ₹ total driver bata for trip
cleaner_bata: float       # ₹ total cleaner bata (0 for tempo)
halt_cost: float          # ₹ night halt (0 if < 12h round trip)
breakdown_reserve: float  # ₹ breakdown buffer
permit_cost: float        # ₹ interstate permit (0 if same state)
rto_buffer: float         # ₹ RTO friction
loading_hamali: float     # ₹ regional loading hamali
unloading_hamali: float   # ₹ regional unloading hamali
```

### `MandiComparison` additions
```python
# Route & Time
travel_time_hours: float
route_type: str                    # "highway" | "mixed" | "hill"
is_interstate: bool
diesel_price_used: float

# Spoilage
spoilage_percent: float            # % quantity lost
weight_loss_percent: float
grade_discount_percent: float
net_saleable_quantity_kg: float

# Price Analytics
price_date: date                   # already fetched, now surfaced
price_volatility_7d: float         # coefficient of variation %
price_trend: str                   # "rising" | "falling" | "stable"

# Risk & Confidence
risk_score: float                  # 0–100
confidence_score: float            # 0–100
stability_class: str               # "stable" | "moderate" | "volatile"

# Stress Test
stress_test: StressTestResult      # nested object

# Guardrail
economic_warning: str | None       # None if all checks pass
```

### New `StressTestResult` schema
```python
class StressTestResult(BaseModel):
    worst_case_profit: float
    break_even_price_per_kg: float
    margin_of_safety_pct: float
    verdict_survives_stress: bool   # True if worst_case_profit > 0
```

---

## Performance Constraints

| Constraint | Approach |
|------------|----------|
| Max 25 mandis evaluated | Hard cap in pre-filter (configurable via settings) |
| No full price_history scans | All queries date-bounded; 7-day window for volatility |
| OSRM parallelism | ThreadPoolExecutor(max_workers=10) — unchanged |
| Target response time | < 700ms (warm cache), < 5s (cold, 25 OSRM calls) |
| Price analytics per mandi | Batched in single SQL query before OSRM loop |

---

## No New DB Tables Required

All new logic is computational. The existing `road_distance_cache` table satisfies routing.
Volatility/trend are derived from existing `price_history` rows.
Diesel price and config params live in `settings` (`.env` overrideable).

---

## Files Changed Summary

| File | Status | Key Change |
|------|--------|------------|
| `transport/economics.py` | NEW | Freight engine: diesel, bata, permit, breakdown |
| `transport/spoilage.py` | NEW | Exponential spoilage, weight loss, hamali |
| `transport/price_analytics.py` | NEW | Volatility, trend, confidence |
| `transport/risk_engine.py` | NEW | Risk score, stress test, behavioral, guardrails |
| `transport/service.py` | MODIFIED | Orchestrator wiring all new modules |
| `transport/schemas.py` | MODIFIED | +14 new fields, StressTestResult schema |
| `transport/routes.py` | MINOR | Expose new fields, update /calculate with time |
| `core/config.py` | MODIFIED | 4 new transport settings |
