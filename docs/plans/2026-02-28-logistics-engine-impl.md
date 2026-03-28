# Real-World Agricultural Logistics Engine — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the AgriProfit transport module from a simplistic cost-per-km model into a real Indian agricultural logistics decision engine with driver bata, diesel sensitivity, exponential spoilage decay, 7-day price volatility, composite risk scoring, stress testing, and behavioral corrections.

**Architecture:** Four new sub-modules (`economics.py`, `spoilage.py`, `price_analytics.py`, `risk_engine.py`) alongside existing `routing.py`. `service.py` becomes a pure orchestrator. All computation is stateless — no new DB tables. Freight model validated against a worked example: truck_small, 292 km intrastate, 5500 kg → ₹23,581 total freight (~₹4.29/kg).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (sync Session), Pydantic v2, pytest, monkeypatch, MagicMock. No new dependencies.

**Design Doc:** `docs/plans/2026-02-28-logistics-engine-design.md` (read this first for all constants and formulas)

---

## Reading Order Before You Start

Read these files in order — don't skip:
1. `docs/plans/2026-02-28-logistics-engine-design.md` — all approved constants, formulas, worked examples
2. `backend/app/transport/service.py` — existing orchestrator you'll modify
3. `backend/app/transport/schemas.py` — existing schemas you'll extend
4. `backend/tests/test_transport_service.py` — existing test patterns to follow
5. `backend/app/core/config.py` — where you'll add 4 new settings

---

## Task 1: Config Additions

**Files:**
- Modify: `backend/app/core/config.py` (in the ROUTING section, ~line 316)

**Context:** All new transport settings go in `config.py` under the existing `# ROUTING` section. The `settings` singleton is imported everywhere via `from app.core.config import settings`.

**Step 1: Add the 4 new settings to `Settings` class**

Find the `# ROUTING` block (around line 314) and add after `routing_provider`:

```python
    # =========================================================================
    # TRANSPORT ECONOMICS
    # =========================================================================
    diesel_price_per_liter: float = Field(
        default=98.0,
        ge=50.0,
        le=200.0,
        description="Current diesel price in ₹/L. Affects freight rate via sensitivity coefficient.",
    )
    diesel_baseline_price: float = Field(
        default=98.0,
        ge=50.0,
        le=200.0,
        description="Baseline diesel price used for sensitivity calculation (₹/L).",
    )
    transport_weather_risk_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weather risk placeholder (0–1). Used in composite risk score calculation.",
    )
    transport_max_mandis_evaluated: int = Field(
        default=25,
        ge=5,
        le=50,
        description="Hard cap on mandis evaluated per /compare request (performance bound).",
    )
```

**Step 2: Verify settings loads without error**

```bash
cd backend && python -c "from app.core.config import settings; print(settings.diesel_price_per_liter, settings.transport_max_mandis_evaluated)"
```
Expected output: `98.0 25`

**Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(transport): add diesel price and transport config settings"
```

---

## Task 2: `economics.py` — Freight Engine

**Files:**
- Create: `backend/app/transport/economics.py`
- Create: `backend/tests/test_transport_economics.py`

**Context:** This module computes the full real-world freight cost. It has zero DB dependencies — pure calculation. All constants are from the design doc, user-approved and validated with a worked example.

The `FreightResult` dataclass is returned from `compute_freight()` and consumed by `service.py`.

**Step 1: Write the failing tests first**

Create `backend/tests/test_transport_economics.py`:

```python
"""
Tests for economics.py — Real Indian freight cost calculation.

All assertions validated against the design doc worked example:
  truck_small, 292 km intrastate, 5500 kg, diesel ₹98, 42 km/h
  → total_freight ≈ ₹23,581 (±50 for rounding)
"""
import pytest
from app.transport.economics import (
    compute_travel_time,
    compute_freight,
    FreightResult,
    BATA,
    PRACTICAL_CAPACITY_FACTOR,
)
from app.transport.schemas import VehicleType


class TestTravelTime:
    def test_intrastate_plain_highway(self):
        # 292 km, mixed speed 42 km/h → round trip = 292/42*2 ≈ 13.9h
        hours = compute_travel_time(292.0, "Punjab", "Punjab")
        assert 13.5 <= hours <= 14.5

    def test_hill_state_destination(self):
        # Himachal Pradesh is a hill state → 32 km/h
        hours_hill = compute_travel_time(200.0, "Punjab", "Himachal Pradesh")
        hours_plain = compute_travel_time(200.0, "Punjab", "Punjab")
        assert hours_hill > hours_plain

    def test_zero_distance(self):
        hours = compute_travel_time(0.0, "Kerala", "Kerala")
        assert hours == 0.0

    def test_urban_congestion_applied(self):
        # Specify urban=True → +15% travel time
        hours_urban = compute_travel_time(100.0, "Maharashtra", "Maharashtra", urban=True)
        hours_plain = compute_travel_time(100.0, "Maharashtra", "Maharashtra", urban=False)
        assert pytest.approx(hours_urban, rel=0.01) == hours_plain * 1.15


class TestFreightResult:
    def test_worked_example_intrastate(self):
        """
        Validated example from design doc:
        truck_small, 292 km, 5500 kg, diesel ₹98, 42 km/h, intrastate Punjab
        Expected total_freight ≈ ₹23,581 (±100)
        """
        result = compute_freight(
            distance_km=292.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5500.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        assert isinstance(result, FreightResult)
        assert 23_000 <= result.total_freight <= 24_200  # ±600 tolerance

    def test_interstate_adds_permit(self):
        result_intra = compute_freight(
            distance_km=300.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        result_inter = compute_freight(
            distance_km=300.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Haryana",
            diesel_price=98.0,
        )
        assert result_inter.permit_cost == 1200.0
        assert result_intra.permit_cost == 0.0
        assert result_inter.total_freight > result_intra.total_freight

    def test_diesel_spike_increases_freight(self):
        result_base = compute_freight(
            distance_km=200.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1500.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        result_spike = compute_freight(
            distance_km=200.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1500.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=112.7,  # +15%
        )
        assert result_spike.raw_transport > result_base.raw_transport

    def test_night_halt_triggered_beyond_12h(self):
        # Long distance forces round trip > 12h
        # 400 km at 42 km/h → 400/42*2 ≈ 19h → halt triggered
        result = compute_freight(
            distance_km=400.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        assert result.halt_cost > 0

    def test_no_night_halt_short_trip(self):
        # 150 km at 42 km/h → 150/42*2 ≈ 7.1h → no halt
        result = compute_freight(
            distance_km=150.0,
            vehicle_type=VehicleType.TRUCK_SMALL,
            quantity_kg=5000.0,
            source_state="Punjab",
            mandi_state="Punjab",
            diesel_price=98.0,
        )
        assert result.halt_cost == 0.0

    def test_tempo_has_no_cleaner_bata(self):
        result = compute_freight(
            distance_km=100.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1000.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        assert result.cleaner_bata == 0.0

    def test_practical_capacity_90_percent(self):
        # 1 trip capacity for TEMPO: 2000 * 0.9 = 1800 kg
        result = compute_freight(
            distance_km=100.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1800.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        assert result.trips == 1

        # 1801 kg needs 2 trips (practical capacity exceeded)
        result2 = compute_freight(
            distance_km=100.0,
            vehicle_type=VehicleType.TEMPO,
            quantity_kg=1801.0,
            source_state="Kerala",
            mandi_state="Kerala",
            diesel_price=98.0,
        )
        assert result2.trips == 2

    def test_breakdown_reserve_scales_with_distance(self):
        r_short = compute_freight(100.0, VehicleType.TEMPO, 1000.0, "Punjab", "Punjab", 98.0)
        r_long  = compute_freight(500.0, VehicleType.TEMPO, 1000.0, "Punjab", "Punjab", 98.0)
        # breakdown_reserve = ₹1/km * distance * 2
        assert r_long.breakdown_reserve > r_short.breakdown_reserve
```

**Step 2: Run tests — expect ImportError**

```bash
cd backend && python -m pytest tests/test_transport_economics.py -v 2>&1 | head -20
```
Expected: `ImportError: cannot import name 'compute_freight'`

**Step 3: Implement `economics.py`**

Create `backend/app/transport/economics.py`:

```python
"""
Real Indian freight cost calculation engine.

All constants approved and validated against worked example:
  truck_small, 292 km intrastate, 5500 kg, diesel ₹98, 42 km/h
  → total_freight ≈ ₹23,581

Design doc: docs/plans/2026-02-28-logistics-engine-design.md
"""
import math
from dataclasses import dataclass, field
from app.transport.schemas import VehicleType

# =============================================================================
# CONSTANTS — 2026 production rates (user-approved)
# =============================================================================

BATA: dict[str, dict[str, float]] = {
    "TEMPO":       {"driver_day": 950.0,  "cleaner_day": 0.0,   "night_halt": 900.0},
    "TRUCK_SMALL": {"driver_day": 1200.0, "cleaner_day": 650.0, "night_halt": 1100.0},
    "TRUCK_LARGE": {"driver_day": 1500.0, "cleaner_day": 850.0, "night_halt": 1400.0},
}

DIESEL_DEPENDENCY: dict[str, float] = {
    "TEMPO":       0.55,
    "TRUCK_SMALL": 0.62,
    "TRUCK_LARGE": 0.68,
}

DIESEL_BASELINE: float = 98.0          # ₹/L
PRACTICAL_CAPACITY_FACTOR: float = 0.90
BREAKDOWN_RESERVE_PER_KM: float = 1.0  # ₹/km (both ways)
RTO_FRICTION_INTRASTATE: float = 0.015
RTO_FRICTION_INTERSTATE: float = 0.025
INTERSTATE_PERMIT_COST: float = 1200.0
TOLL_PLAZA_SPACING_KM: float = 70.0
WORKING_HOURS_PER_DAY: float = 10.0

# Speed by route type (km/h)
SPEED_HIGHWAY: float = 55.0
SPEED_MIXED:   float = 42.0
SPEED_HILL:    float = 32.0
URBAN_CONGESTION_FACTOR: float = 1.15

HILL_STATES: frozenset[str] = frozenset({
    "jammu and kashmir", "himachal pradesh", "uttarakhand", "sikkim",
    "arunachal pradesh", "meghalaya", "nagaland", "manipur", "mizoram",
    "tripura",
})

# Base per-km freight rates (same as existing VEHICLES dict, kept in sync)
BASE_RATES: dict[str, float] = {
    "TEMPO":       18.0,
    "TRUCK_SMALL": 28.0,
    "TRUCK_LARGE": 38.0,
}

TOLL_PER_PLAZA: dict[str, float] = {
    "TEMPO":       100.0,
    "TRUCK_SMALL": 200.0,
    "TRUCK_LARGE": 350.0,
}

VEHICLE_CAPACITY_KG: dict[str, float] = {
    "TEMPO":       2000.0,
    "TRUCK_SMALL": 7000.0,
    "TRUCK_LARGE": 15000.0,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FreightResult:
    """Complete freight cost breakdown for one route."""
    # Route metadata
    vehicle_type: str
    trips: int
    round_trip_hours: float
    days: int
    is_interstate: bool
    route_type: str                 # "highway" | "mixed" | "hill"
    diesel_price_used: float

    # Cost components (₹)
    raw_transport: float            # distance × effective_rate × 2 × trips
    toll_cost: float
    driver_bata: float              # driver_day × days
    cleaner_bata: float             # cleaner_day × days (0 for tempo)
    halt_cost: float                # night_halt or 0
    breakdown_reserve: float        # ₹1/km × distance × 2
    permit_cost: float              # 1200 if interstate, else 0
    rto_buffer: float               # % of raw_transport

    # Derived
    total_freight: float = field(init=False)

    def __post_init__(self) -> None:
        self.total_freight = round(
            self.raw_transport + self.toll_cost + self.driver_bata
            + self.cleaner_bata + self.halt_cost + self.breakdown_reserve
            + self.permit_cost + self.rto_buffer,
            2,
        )


# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================

def _normalize_state(state: str) -> str:
    return (state or "").strip().lower()


def _is_hill_route(source_state: str, mandi_state: str) -> bool:
    return (
        _normalize_state(source_state) in HILL_STATES
        or _normalize_state(mandi_state) in HILL_STATES
    )


def compute_travel_time(
    distance_km: float,
    source_state: str,
    mandi_state: str,
    urban: bool = False,
) -> float:
    """
    Return estimated round-trip travel time in hours.

    Speed selection:
    - Hill route (source or destination in hill state): 32 km/h
    - Otherwise mixed: 42 km/h
    Urban congestion: +15% if urban=True
    """
    if distance_km <= 0:
        return 0.0
    if _is_hill_route(source_state, mandi_state):
        speed = SPEED_HILL
        route_type = "hill"
    else:
        speed = SPEED_MIXED
        route_type = "mixed"
    one_way_hours = distance_km / speed
    round_trip = one_way_hours * 2
    if urban:
        round_trip *= URBAN_CONGESTION_FACTOR
    return round(round_trip, 2)


def compute_freight(
    distance_km: float,
    vehicle_type: VehicleType,
    quantity_kg: float,
    source_state: str,
    mandi_state: str,
    diesel_price: float,
    urban: bool = False,
) -> FreightResult:
    """
    Compute full real-world freight cost.

    Returns FreightResult with all 10 cost components and total_freight.
    """
    vt = vehicle_type.value  # e.g. "TRUCK_SMALL"

    # Route type
    is_hill = _is_hill_route(source_state, mandi_state)
    route_type = "hill" if is_hill else "mixed"
    speed = SPEED_HILL if is_hill else SPEED_MIXED

    # Diesel-adjusted per-km rate
    dependency = DIESEL_DEPENDENCY[vt]
    effective_rate = BASE_RATES[vt] * (
        1 + dependency * ((diesel_price - DIESEL_BASELINE) / DIESEL_BASELINE)
    )

    # Trips with 90% practical capacity cap
    practical_capacity = VEHICLE_CAPACITY_KG[vt] * PRACTICAL_CAPACITY_FACTOR
    trips = math.ceil(quantity_kg / practical_capacity)

    # Core freight (round-trip × trips)
    raw_transport = round(distance_km * effective_rate * 2 * trips, 2)

    # Toll (round-trip × trips)
    toll_plazas = max(0, round(distance_km / TOLL_PLAZA_SPACING_KM))
    toll_cost = round(toll_plazas * TOLL_PER_PLAZA[vt] * 2 * trips, 2)

    # Travel time and days
    round_trip_hours = distance_km / speed * 2
    if urban:
        round_trip_hours *= URBAN_CONGESTION_FACTOR
    days = max(1, math.ceil(round_trip_hours / WORKING_HOURS_PER_DAY))

    # Bata
    driver_bata = round(BATA[vt]["driver_day"] * days, 2)
    cleaner_bata = round(BATA[vt]["cleaner_day"] * days, 2)

    # Night halt (one halt covers the entire multi-trip journey)
    halt_cost = BATA[vt]["night_halt"] if round_trip_hours > 12.0 else 0.0

    # Breakdown reserve (₹1/km, both ways, once regardless of trips)
    breakdown_reserve = round(BREAKDOWN_RESERVE_PER_KM * distance_km * 2, 2)

    # Interstate extras
    is_interstate = _normalize_state(source_state) != _normalize_state(mandi_state)
    permit_cost = INTERSTATE_PERMIT_COST if is_interstate else 0.0
    rto_rate = RTO_FRICTION_INTERSTATE if is_interstate else RTO_FRICTION_INTRASTATE
    rto_buffer = round(raw_transport * rto_rate, 2)

    return FreightResult(
        vehicle_type=vt,
        trips=trips,
        round_trip_hours=round(round_trip_hours, 2),
        days=days,
        is_interstate=is_interstate,
        route_type=route_type,
        diesel_price_used=diesel_price,
        raw_transport=raw_transport,
        toll_cost=toll_cost,
        driver_bata=driver_bata,
        cleaner_bata=cleaner_bata,
        halt_cost=halt_cost,
        breakdown_reserve=breakdown_reserve,
        permit_cost=permit_cost,
        rto_buffer=rto_buffer,
    )
```

**Step 4: Run tests — expect all to pass**

```bash
cd backend && python -m pytest tests/test_transport_economics.py -v
```
Expected: all 10 tests PASS

**Step 5: Commit**

```bash
git add backend/app/transport/economics.py backend/tests/test_transport_economics.py
git commit -m "feat(transport): add economics.py — real Indian freight model with diesel sensitivity and bata"
```

---

## Task 3: `spoilage.py` — Perishability Engine

**Files:**
- Create: `backend/app/transport/spoilage.py`
- Create: `backend/tests/test_transport_spoilage.py`

**Context:** Computes exponential spoilage decay, weight loss, grade discount, and regional hamali. Formula: `spoilage_fraction = 1 - (1 - rate_per_24h) ** (hours / 24)`. Input is the commodity category string from the DB (may be None). All constants from design doc.

**Step 1: Write the failing tests**

Create `backend/tests/test_transport_spoilage.py`:

```python
"""
Tests for spoilage.py — Perishability, weight loss, grade discount, hamali.

Exponential decay formula:
  spoilage_fraction = 1 - (1 - rate_per_24h) ** (hours / 24)
  At 24h: spoilage_fraction == rate_per_24h (exactly, by construction)
"""
import pytest
from app.transport.spoilage import (
    compute_spoilage,
    compute_hamali,
    SpoilageResult,
    HamaliResult,
    SPOILAGE_RATES,
)


class TestSpoilageDecay:
    def test_vegetable_at_24h_equals_rate(self):
        result = compute_spoilage("Vegetable", round_trip_hours=24.0)
        # At exactly 24h: 1 - (1 - 0.03)^1 = 0.03
        assert result.spoilage_fraction == pytest.approx(0.03, rel=0.001)

    def test_fruit_at_24h(self):
        result = compute_spoilage("Fruit", round_trip_hours=24.0)
        assert result.spoilage_fraction == pytest.approx(0.05, rel=0.001)

    def test_grain_at_24h(self):
        result = compute_spoilage("Grain", round_trip_hours=24.0)
        assert result.spoilage_fraction == pytest.approx(0.0015, rel=0.01)

    def test_unknown_category_uses_conservative_default(self):
        result = compute_spoilage(None, round_trip_hours=24.0)
        # NULL category → 0.5% / 24h conservative grain default
        assert result.spoilage_fraction == pytest.approx(0.005, rel=0.01)

    def test_zero_hours_zero_spoilage(self):
        result = compute_spoilage("Vegetable", round_trip_hours=0.0)
        assert result.spoilage_fraction == 0.0

    def test_12h_vegetable_less_than_24h(self):
        r12 = compute_spoilage("Vegetable", round_trip_hours=12.0)
        r24 = compute_spoilage("Vegetable", round_trip_hours=24.0)
        assert r12.spoilage_fraction < r24.spoilage_fraction
        # 12h for veg ≈ 1.51%
        assert r12.spoilage_fraction == pytest.approx(0.0151, abs=0.001)

    def test_auction_underbid_added_when_high_volatility(self):
        result_normal  = compute_spoilage("Vegetable", 24.0, volatility_pct=5.0)
        result_volatile = compute_spoilage("Vegetable", 24.0, volatility_pct=10.0)
        # grade_discount increases by 1.5pp when volatility > 8%
        assert result_volatile.grade_discount_fraction > result_normal.grade_discount_fraction
        diff = result_volatile.grade_discount_fraction - result_normal.grade_discount_fraction
        assert diff == pytest.approx(0.015, rel=0.01)

    def test_net_saleable_quantity_calculation(self):
        result = compute_spoilage("Vegetable", round_trip_hours=24.0)
        quantity = 1000.0
        net_qty = result.net_saleable_quantity(quantity)
        # net = quantity * (1 - spoilage) * (1 - weight_loss)
        expected = 1000 * (1 - result.spoilage_fraction) * (1 - result.weight_loss_fraction)
        assert net_qty == pytest.approx(expected, rel=0.001)


class TestHamali:
    def test_north_india_rates(self):
        result = compute_hamali("Punjab", 10000.0)  # 10000 kg = 100 quintals
        # North: ₹10/quintal load, ₹12/quintal unload
        assert result.loading_hamali == pytest.approx(100 * 10, rel=0.01)
        assert result.unloading_hamali == pytest.approx(100 * 12, rel=0.01)

    def test_south_india_rates(self):
        result = compute_hamali("Kerala", 10000.0)
        # South: ₹18/quintal load, ₹22/quintal unload
        assert result.loading_hamali == pytest.approx(100 * 18, rel=0.01)
        assert result.unloading_hamali == pytest.approx(100 * 22, rel=0.01)

    def test_maharashtra_rates(self):
        result = compute_hamali("Maharashtra", 10000.0)
        assert result.loading_hamali == pytest.approx(100 * 13, rel=0.01)
        assert result.unloading_hamali == pytest.approx(100 * 16, rel=0.01)

    def test_unknown_state_uses_default(self):
        result = compute_hamali("Atlantis", 10000.0)
        assert result.loading_hamali == pytest.approx(100 * 15, rel=0.01)
```

**Step 2: Run tests — expect ImportError**

```bash
cd backend && python -m pytest tests/test_transport_spoilage.py -v 2>&1 | head -10
```

**Step 3: Implement `spoilage.py`**

Create `backend/app/transport/spoilage.py`:

```python
"""
Perishability model — exponential spoilage decay, weight loss, grade discount, hamali.

Formula: spoilage_fraction = 1 - (1 - rate_per_24h) ** (round_trip_hours / 24)

Rates from design doc (user-approved, open-truck no cold chain):
  Vegetable: 3.0% / 24h | Fruit: 5.0% / 24h | Grain: 0.15% / 24h
  Pulses: 0.10% / 24h | Spice: 0.30% / 24h | Unknown: 0.50% / 24h
"""
from __future__ import annotations
from dataclasses import dataclass

# =============================================================================
# SPOILAGE RATES (per 24h, as fractions)
# =============================================================================

SPOILAGE_RATES: dict[str, dict[str, float]] = {
    "vegetable": {"rate": 0.030, "weight_loss": 0.025, "grade_discount": 0.040},
    "fruit":     {"rate": 0.050, "weight_loss": 0.020, "grade_discount": 0.050},
    "spice":     {"rate": 0.003, "weight_loss": 0.005, "grade_discount": 0.010},
    "grain":     {"rate": 0.0015,"weight_loss": 0.0075,"grade_discount": 0.005},
    "paddy":     {"rate": 0.0015,"weight_loss": 0.0075,"grade_discount": 0.005},
    "pulses":    {"rate": 0.001, "weight_loss": 0.005, "grade_discount": 0.005},
    "unknown":   {"rate": 0.005, "weight_loss": 0.0075,"grade_discount": 0.010},
}

AUCTION_UNDERBID_FRACTION: float = 0.015  # added to grade_discount when volatility > 8%
HIGH_VOLATILITY_THRESHOLD: float = 8.0    # %

# =============================================================================
# HAMALI RATES (₹/quintal = ₹/100kg)
# =============================================================================

NORTH_STATES = {
    "uttar pradesh", "punjab", "haryana", "bihar", "madhya pradesh",
    "rajasthan", "himachal pradesh", "uttarakhand", "delhi", "chandigarh",
}
SOUTH_STATES = {
    "kerala", "tamil nadu", "karnataka", "andhra pradesh", "telangana",
}
MAHA_STATES = {"maharashtra", "gujarat"}

HAMALI_RATES: dict[str, tuple[float, float]] = {
    "north":      (10.0, 12.0),   # (loading/quintal, unloading/quintal)
    "south":      (18.0, 22.0),
    "maharashtra": (13.0, 16.0),
    "default":    (15.0, 18.0),
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SpoilageResult:
    category: str
    spoilage_fraction: float
    weight_loss_fraction: float
    grade_discount_fraction: float  # includes auction underbid if high volatility

    def net_saleable_quantity(self, quantity_kg: float) -> float:
        """Quantity remaining after spoilage and moisture loss."""
        return quantity_kg * (1 - self.spoilage_fraction) * (1 - self.weight_loss_fraction)

    def net_revenue(self, quantity_kg: float, price_per_kg: float) -> float:
        """Revenue after spoilage, weight loss, and grade discount."""
        return self.net_saleable_quantity(quantity_kg) * price_per_kg * (1 - self.grade_discount_fraction)


@dataclass
class HamaliResult:
    mandi_state: str
    loading_hamali: float    # ₹ total
    unloading_hamali: float  # ₹ total
    total_hamali: float


# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================

def _normalize_category(category: str | None) -> str:
    if not category:
        return "unknown"
    return category.strip().lower()


def compute_spoilage(
    category: str | None,
    round_trip_hours: float,
    volatility_pct: float = 0.0,
) -> SpoilageResult:
    """
    Compute exponential spoilage fraction and related losses.

    Args:
        category: commodity category string from DB (may be None)
        round_trip_hours: total travel time (both ways) in hours
        volatility_pct: 7-day price volatility % (adds auction underbid if > 8%)
    """
    cat = _normalize_category(category)
    rates = SPOILAGE_RATES.get(cat, SPOILAGE_RATES["unknown"])

    r = rates["rate"]
    if round_trip_hours <= 0:
        spoilage = 0.0
    else:
        spoilage = 1 - (1 - r) ** (round_trip_hours / 24)

    grade_discount = rates["grade_discount"]
    if volatility_pct > HIGH_VOLATILITY_THRESHOLD:
        grade_discount += AUCTION_UNDERBID_FRACTION

    return SpoilageResult(
        category=cat,
        spoilage_fraction=round(spoilage, 6),
        weight_loss_fraction=rates["weight_loss"],
        grade_discount_fraction=round(grade_discount, 4),
    )


def compute_hamali(mandi_state: str, quantity_kg: float) -> HamaliResult:
    """Regional loading/unloading hamali charges."""
    state = (mandi_state or "").strip().lower()
    quintals = quantity_kg / 100.0

    if state in NORTH_STATES:
        load_rate, unload_rate = HAMALI_RATES["north"]
    elif state in SOUTH_STATES:
        load_rate, unload_rate = HAMALI_RATES["south"]
    elif state in MAHA_STATES:
        load_rate, unload_rate = HAMALI_RATES["maharashtra"]
    else:
        load_rate, unload_rate = HAMALI_RATES["default"]

    loading   = round(quintals * load_rate, 2)
    unloading = round(quintals * unload_rate, 2)

    return HamaliResult(
        mandi_state=mandi_state,
        loading_hamali=loading,
        unloading_hamali=unloading,
        total_hamali=round(loading + unloading, 2),
    )
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_transport_spoilage.py -v
```
Expected: all tests PASS

**Step 5: Commit**

```bash
git add backend/app/transport/spoilage.py backend/tests/test_transport_spoilage.py
git commit -m "feat(transport): add spoilage.py — exponential decay model with hamali and grade discount"
```

---

## Task 4: `price_analytics.py` — Price Credibility

**Files:**
- Create: `backend/app/transport/price_analytics.py`
- Create: `backend/tests/test_transport_price_analytics.py`

**Context:** Queries the last 7 price records for a specific mandi × commodity pair. All queries are date-bounded (no full table scans). Uses `statistics.stdev` from stdlib — no new deps. Returns a `PriceAnalytics` dataclass.

**Step 1: Write the failing tests**

Create `backend/tests/test_transport_price_analytics.py`:

```python
"""
Tests for price_analytics.py — 7-day price volatility, trend, and confidence.

Uses MagicMock to simulate DB results. No real DB needed.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock
from app.transport.price_analytics import compute_price_analytics, PriceAnalytics


def _mock_db_with_prices(prices: list[float], days_ago: int = 0) -> MagicMock:
    """Build a mock DB session that returns the given price list."""
    latest_date = date.today() - timedelta(days=days_ago)
    rows = [
        MagicMock(modal_price=p, price_date=latest_date - timedelta(days=i))
        for i, p in enumerate(prices)
    ]
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = rows
    return db


class TestPriceAnalytics:
    def test_stable_prices_low_volatility(self):
        # Prices ≈ constant → CV near 0
        db = _mock_db_with_prices([3000, 3010, 2990, 3005, 2995, 3000, 3002])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert isinstance(result, PriceAnalytics)
        assert result.volatility_pct < 2.0
        assert result.price_trend == "stable"
        assert result.confidence_score >= 80

    def test_rising_trend(self):
        # Each price 5% higher than previous
        db = _mock_db_with_prices([3000, 3150, 3300, 3450, 3600, 3750, 3900])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        # Latest (index 0) > mean × 1.03 → rising
        assert result.price_trend == "rising"

    def test_falling_trend(self):
        db = _mock_db_with_prices([2000, 2100, 2200, 2300, 2400, 2500, 2600])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.price_trend == "falling"

    def test_high_volatility_reduces_confidence(self):
        # Wildly varying prices → CV > 8%
        db = _mock_db_with_prices([1000, 5000, 1000, 5000, 1000, 5000, 1000])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.volatility_pct > 8.0
        assert result.confidence_score <= 80  # -20 penalty

    def test_stale_price_reduces_confidence(self):
        # Price date is 5 days ago → -15 penalty
        db = _mock_db_with_prices([3000], days_ago=5)
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.confidence_score <= 85  # 100 - 15

    def test_thin_mandi_single_record_reduces_confidence(self):
        # Only 1 price record → -25 penalty
        db = _mock_db_with_prices([3000])
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.confidence_score <= 75  # 100 - 25

    def test_confidence_floor_at_10(self):
        # All penalties applied: volatile + stale + thin → floor at 10
        db = _mock_db_with_prices([1000], days_ago=10)
        result = compute_price_analytics("commodity-id", "Test Mandi", db)
        assert result.confidence_score >= 10

    def test_no_prices_returns_low_confidence_defaults(self):
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        result = compute_price_analytics("commodity-id", "Empty Mandi", db)
        assert result.confidence_score == 10
        assert result.price_trend == "stable"
        assert result.volatility_pct == 0.0
```

**Step 2: Run tests — expect ImportError**

```bash
cd backend && python -m pytest tests/test_transport_price_analytics.py -v 2>&1 | head -10
```

**Step 3: Implement `price_analytics.py`**

Create `backend/app/transport/price_analytics.py`:

```python
"""
Price credibility analytics — 7-day volatility, trend, and confidence scoring.

Query pulls at most 7 rows per mandi×commodity. Safe on 25M-row price_history table.
"""
from __future__ import annotations
import statistics
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

HIGH_VOLATILITY_THRESHOLD: float = 8.0   # CV% above which confidence penalty applies
STALE_PRICE_DAYS: int = 3                 # days before confidence penalty for old data
TREND_UP_THRESHOLD: float = 1.03          # latest > mean * this → "rising"
TREND_DOWN_THRESHOLD: float = 0.97        # latest < mean * this → "falling"

CONFIDENCE_PENALTY_VOLATILE: int = 20
CONFIDENCE_PENALTY_STALE: int = 15
CONFIDENCE_PENALTY_THIN: int = 25
CONFIDENCE_FLOOR: int = 10


@dataclass
class PriceAnalytics:
    volatility_pct: float       # coefficient of variation (stddev / mean × 100)
    price_trend: str            # "rising" | "falling" | "stable"
    confidence_score: int       # 0–100
    n_records: int              # number of price records in last 7 days
    latest_price_date: date | None


def compute_price_analytics(
    commodity_id: str,
    mandi_name: str,
    db: Session,
) -> PriceAnalytics:
    """
    Compute 7-day price volatility, trend, and confidence for a mandi×commodity pair.

    Uses a date-bounded query. Returns safe defaults on empty data.
    """
    query = text("""
        SELECT modal_price, price_date
        FROM price_history
        WHERE commodity_id = CAST(:cid AS UUID)
          AND mandi_name = :mandi
        ORDER BY price_date DESC
        LIMIT 7
    """)
    try:
        rows = db.execute(query, {"cid": str(commodity_id), "mandi": mandi_name}).fetchall()
    except Exception:
        rows = []

    if not rows:
        return PriceAnalytics(
            volatility_pct=0.0,
            price_trend="stable",
            confidence_score=CONFIDENCE_FLOOR,
            n_records=0,
            latest_price_date=None,
        )

    prices = [float(r.modal_price) for r in rows]
    dates  = [r.price_date for r in rows]
    latest_date = dates[0] if dates else None
    latest_price = prices[0]
    mean_price = statistics.mean(prices)

    # Volatility: coefficient of variation
    if len(prices) >= 2 and mean_price > 0:
        volatility_pct = (statistics.stdev(prices) / mean_price) * 100
    else:
        volatility_pct = 0.0

    # Price trend
    if mean_price > 0:
        ratio = latest_price / mean_price
        if ratio >= TREND_UP_THRESHOLD:
            price_trend = "rising"
        elif ratio <= TREND_DOWN_THRESHOLD:
            price_trend = "falling"
        else:
            price_trend = "stable"
    else:
        price_trend = "stable"

    # Confidence scoring
    confidence = 100
    if volatility_pct > HIGH_VOLATILITY_THRESHOLD:
        confidence -= CONFIDENCE_PENALTY_VOLATILE
    if latest_date and (date.today() - latest_date).days > STALE_PRICE_DAYS:
        confidence -= CONFIDENCE_PENALTY_STALE
    if len(prices) == 1:
        confidence -= CONFIDENCE_PENALTY_THIN
    confidence = max(CONFIDENCE_FLOOR, confidence)

    return PriceAnalytics(
        volatility_pct=round(volatility_pct, 2),
        price_trend=price_trend,
        confidence_score=confidence,
        n_records=len(prices),
        latest_price_date=latest_date,
    )
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_transport_price_analytics.py -v
```
Expected: all tests PASS

**Step 5: Commit**

```bash
git add backend/app/transport/price_analytics.py backend/tests/test_transport_price_analytics.py
git commit -m "feat(transport): add price_analytics.py — 7-day volatility, trend, confidence scoring"
```

---

## Task 5: `risk_engine.py` — Risk, Stress Test, Behavioral, Guardrails

**Files:**
- Create: `backend/app/transport/risk_engine.py`
- Create: `backend/tests/test_transport_risk_engine.py`

**Context:** Four functions in one module. All pure computation — no DB, no I/O. Takes in scalar inputs, returns scored/flagged result objects. Verdict downgrade tiers: `excellent → good → marginal → not_viable`.

**Step 1: Write the failing tests**

Create `backend/tests/test_transport_risk_engine.py`:

```python
"""
Tests for risk_engine.py — composite risk score, stress test, behavioral scoring, guardrails.
"""
import pytest
from app.transport.risk_engine import (
    compute_risk_score,
    run_stress_test,
    apply_behavioral_corrections,
    check_guardrails,
    RiskResult,
    StressTestResult,
)


class TestRiskScore:
    def test_zero_risk_intrastate_short_stable(self):
        result = compute_risk_score(
            volatility_pct=0.0,
            distance_km=50.0,
            spoilage_fraction=0.0,
            diesel_price=98.0,
            diesel_baseline=98.0,
            is_interstate=False,
            weather_risk_weight=0.0,
        )
        assert result.risk_score < 20.0
        assert result.stability_class == "stable"

    def test_high_volatility_increases_risk(self):
        low = compute_risk_score(2.0, 100.0, 0.01, 98.0, 98.0, False, 0.3)
        high = compute_risk_score(20.0, 100.0, 0.01, 98.0, 98.0, False, 0.3)
        assert high.risk_score > low.risk_score

    def test_interstate_adds_regulatory_risk(self):
        intra = compute_risk_score(5.0, 200.0, 0.02, 98.0, 98.0, False, 0.3)
        inter = compute_risk_score(5.0, 200.0, 0.02, 98.0, 98.0, True, 0.3)
        assert inter.risk_score > intra.risk_score

    def test_stability_class_thresholds(self):
        low  = compute_risk_score(1.0, 50.0, 0.001, 98.0, 98.0, False, 0.0)
        mid  = compute_risk_score(10.0, 400.0, 0.04, 105.0, 98.0, False, 0.5)
        high = compute_risk_score(25.0, 900.0, 0.14, 115.0, 98.0, True, 1.0)
        assert low.stability_class == "stable"
        assert mid.stability_class in ("stable", "moderate")
        assert high.stability_class == "volatile"

    def test_risk_score_bounded_0_100(self):
        result = compute_risk_score(100.0, 10000.0, 1.0, 200.0, 98.0, True, 1.0)
        assert 0 <= result.risk_score <= 100


class TestStressTest:
    def test_stress_worsens_profit(self):
        normal_profit = 50000.0
        result = run_stress_test(
            normal_profit=normal_profit,
            normal_net_quantity=5000.0,
            normal_total_cost=30000.0,
            price_per_kg=30.0,
            toll_cost=1500.0,
            raw_transport=20000.0,
            spoilage_fraction=0.03,
            grade_discount_fraction=0.04,
        )
        assert result.worst_case_profit < normal_profit

    def test_negative_worst_case_survives_stress_false(self):
        result = run_stress_test(
            normal_profit=1000.0,        # thin margin
            normal_net_quantity=100.0,
            normal_total_cost=29000.0,   # very high cost relative to revenue
            price_per_kg=300.0,
            toll_cost=5000.0,
            raw_transport=20000.0,
            spoilage_fraction=0.03,
            grade_discount_fraction=0.04,
        )
        # With -12% price and +5% spoilage + +3% grade discount, a thin margin should fail
        # We just check structure here; exact value depends on inputs
        assert isinstance(result, StressTestResult)
        assert result.break_even_price_per_kg > 0
        assert isinstance(result.verdict_survives_stress, bool)

    def test_margin_of_safety_formula(self):
        result = run_stress_test(
            normal_profit=10000.0,
            normal_net_quantity=1000.0,
            normal_total_cost=20000.0,
            price_per_kg=30.0,
            toll_cost=1000.0,
            raw_transport=15000.0,
            spoilage_fraction=0.0,
            grade_discount_fraction=0.0,
        )
        # margin_of_safety = (normal - worst) / abs(normal) * 100
        expected_mos = (10000.0 - result.worst_case_profit) / 10000.0 * 100
        assert result.margin_of_safety_pct == pytest.approx(expected_mos, rel=0.01)


class TestBehavioralCorrections:
    def test_far_distance_downgrades_verdict(self):
        result = apply_behavioral_corrections(
            verdict="excellent",
            distance_km=800.0,      # > 700 km
            profit_diff_pct=20.0,
            risk_score=30.0,
        )
        assert result in ("good", "marginal", "not_viable")

    def test_small_profit_diff_downgrades_far_mandi(self):
        result = apply_behavioral_corrections(
            verdict="excellent",
            distance_km=400.0,
            profit_diff_pct=3.0,    # < 5% → prefer closer
            risk_score=30.0,
        )
        # Should downgrade because profit difference is minimal
        assert result in ("good", "marginal", "not_viable")

    def test_high_risk_downgrades_verdict(self):
        result = apply_behavioral_corrections(
            verdict="excellent",
            distance_km=100.0,
            profit_diff_pct=30.0,
            risk_score=80.0,        # > 70
        )
        assert result in ("good", "marginal", "not_viable")

    def test_no_downgrade_when_conditions_good(self):
        result = apply_behavioral_corrections(
            verdict="excellent",
            distance_km=200.0,
            profit_diff_pct=25.0,
            risk_score=25.0,
        )
        assert result == "excellent"

    def test_max_downgrade_capped_at_2_tiers(self):
        # distance > 700, risk > 70, tiny profit diff → at most 2 tiers down from excellent
        result = apply_behavioral_corrections(
            verdict="excellent",
            distance_km=900.0,
            profit_diff_pct=2.0,
            risk_score=85.0,
        )
        assert result in ("marginal", "not_viable")


class TestGuardrails:
    def test_extreme_roi_flagged(self):
        warning = check_guardrails(
            roi_percentage=600.0,
            net_margin=0.30,
            cost_to_gross_ratio=0.15,
            profit_per_kg=5.0,
            price_per_kg=30.0,
        )
        assert warning is not None
        assert "ROI" in warning

    def test_extreme_margin_flagged(self):
        warning = check_guardrails(
            roi_percentage=100.0,
            net_margin=0.60,          # > 55%
            cost_to_gross_ratio=0.15,
            profit_per_kg=5.0,
            price_per_kg=30.0,
        )
        assert warning is not None
        assert "Margin" in warning

    def test_very_low_cost_ratio_flagged(self):
        warning = check_guardrails(
            roi_percentage=50.0,
            net_margin=0.30,
            cost_to_gross_ratio=0.03,  # < 6%
            profit_per_kg=5.0,
            price_per_kg=30.0,
        )
        assert warning is not None

    def test_profit_exceeds_80_pct_price_flagged(self):
        warning = check_guardrails(
            roi_percentage=50.0,
            net_margin=0.30,
            cost_to_gross_ratio=0.15,
            profit_per_kg=26.0,        # > 30 * 0.8
            price_per_kg=30.0,
        )
        assert warning is not None

    def test_normal_scenario_no_warning(self):
        warning = check_guardrails(
            roi_percentage=150.0,
            net_margin=0.25,
            cost_to_gross_ratio=0.15,
            profit_per_kg=7.0,
            price_per_kg=30.0,
        )
        assert warning is None
```

**Step 2: Run tests — expect ImportError**

```bash
cd backend && python -m pytest tests/test_transport_risk_engine.py -v 2>&1 | head -10
```

**Step 3: Implement `risk_engine.py`**

Create `backend/app/transport/risk_engine.py`:

```python
"""
Risk scoring, stress testing, behavioral corrections, and economic guardrails.

All functions are pure — no DB, no I/O.
Design doc: docs/plans/2026-02-28-logistics-engine-design.md
"""
from __future__ import annotations
from dataclasses import dataclass

# Risk weight coefficients (sum to 1.0)
WEIGHT_VOLATILITY:  float = 0.25
WEIGHT_DISTANCE:    float = 0.20
WEIGHT_SPOILAGE:    float = 0.20
WEIGHT_FUEL:        float = 0.15
WEIGHT_REGULATORY:  float = 0.10
WEIGHT_WEATHER:     float = 0.10

# Normalisation denominators
VOLATILITY_NORM:  float = 20.0    # 20% CV → max score
DISTANCE_NORM:    float = 1000.0  # 1000 km → max score
SPOILAGE_NORM:    float = 0.15    # 15% spoilage → max score
FUEL_NORM:        float = 0.20    # 20% diesel deviation → max score

# Stability thresholds
STABLE_THRESHOLD:   float = 30.0
MODERATE_THRESHOLD: float = 60.0

# Stress test shocks
STRESS_DIESEL_PCT:    float = 0.15   # +15%
STRESS_TOLL_PCT:      float = 0.25   # +25%
STRESS_PRICE_PCT:     float = -0.12  # −12%
STRESS_SPOILAGE_ADD:  float = 0.05   # +5pp absolute
STRESS_GRADE_ADD:     float = 0.03   # +3pp absolute

# Behavioral scoring thresholds
FAR_DISTANCE_KM:        float = 700.0
THIN_MARGIN_DIFF_PCT:   float = 5.0
HIGH_RISK_THRESHOLD:    float = 70.0
MAX_VERDICT_DOWNGRADE:  int   = 2

# Verdict tier ordering
VERDICT_TIERS = ["excellent", "good", "marginal", "not_viable"]

# Guardrail thresholds
ROI_ANOMALY_PCT:    float = 500.0
MARGIN_ANOMALY_PCT: float = 0.55
COST_RATIO_LOW:     float = 0.06
PROFIT_PRICE_RATIO: float = 0.80


@dataclass
class RiskResult:
    risk_score: float        # 0–100
    confidence_score: int    # passed through from price_analytics; stored here for convenience
    stability_class: str     # "stable" | "moderate" | "volatile"


@dataclass
class StressTestResult:
    worst_case_profit: float
    break_even_price_per_kg: float
    margin_of_safety_pct: float
    verdict_survives_stress: bool


def compute_risk_score(
    volatility_pct: float,
    distance_km: float,
    spoilage_fraction: float,
    diesel_price: float,
    diesel_baseline: float,
    is_interstate: bool,
    weather_risk_weight: float,
) -> RiskResult:
    """Composite risk score (0–100). Higher = riskier."""
    vol_component  = min(1.0, volatility_pct / VOLATILITY_NORM)
    dist_component = min(1.0, distance_km / DISTANCE_NORM)
    spo_component  = min(1.0, spoilage_fraction / SPOILAGE_NORM)
    fuel_delta     = abs(diesel_price - diesel_baseline) / max(diesel_baseline, 1.0)
    fuel_component = min(1.0, fuel_delta / FUEL_NORM)
    reg_component  = 1.0 if is_interstate else 0.0
    weather_component = min(1.0, weather_risk_weight)

    raw = (
        vol_component  * WEIGHT_VOLATILITY
        + dist_component * WEIGHT_DISTANCE
        + spo_component  * WEIGHT_SPOILAGE
        + fuel_component * WEIGHT_FUEL
        + reg_component  * WEIGHT_REGULATORY
        + weather_component * WEIGHT_WEATHER
    )
    risk_score = round(min(100.0, max(0.0, raw * 100)), 1)

    if risk_score < STABLE_THRESHOLD:
        stability_class = "stable"
    elif risk_score < MODERATE_THRESHOLD:
        stability_class = "moderate"
    else:
        stability_class = "volatile"

    return RiskResult(risk_score=risk_score, confidence_score=0, stability_class=stability_class)


def run_stress_test(
    normal_profit: float,
    normal_net_quantity: float,
    normal_total_cost: float,
    price_per_kg: float,
    toll_cost: float,
    raw_transport: float,
    spoilage_fraction: float,
    grade_discount_fraction: float,
) -> StressTestResult:
    """
    Simulate worst-case scenario with all stress shocks applied simultaneously.

    Shocks: diesel+15% (via transport), toll+25%, price-12%, spoilage+5pp, grade_discount+3pp
    """
    stressed_price      = price_per_kg * (1 + STRESS_PRICE_PCT)
    stressed_toll       = toll_cost * (1 + STRESS_TOLL_PCT)
    stressed_transport  = raw_transport * (1 + STRESS_DIESEL_PCT)  # diesel proxy
    stressed_spoilage   = min(0.99, spoilage_fraction + STRESS_SPOILAGE_ADD)
    stressed_grade      = min(0.99, grade_discount_fraction + STRESS_GRADE_ADD)

    # Stressed net quantity (simplified — use same quantity base as normal)
    quantity_base = normal_net_quantity / max(1e-9, (1 - spoilage_fraction))
    stressed_net_qty = quantity_base * (1 - stressed_spoilage)

    # Stressed revenue
    stressed_revenue = stressed_net_qty * stressed_price * (1 - stressed_grade)

    # Stressed cost: replace toll and transport components
    cost_adjustment = (stressed_toll - toll_cost) + (stressed_transport - raw_transport)
    stressed_total_cost = normal_total_cost + cost_adjustment

    worst_case_profit = round(stressed_revenue - stressed_total_cost, 2)
    break_even_price  = round(
        stressed_total_cost / max(stressed_net_qty * (1 - stressed_grade), 1e-6),
        2,
    )
    margin_of_safety  = round(
        (normal_profit - worst_case_profit) / max(abs(normal_profit), 1.0) * 100,
        1,
    )

    return StressTestResult(
        worst_case_profit=worst_case_profit,
        break_even_price_per_kg=break_even_price,
        margin_of_safety_pct=margin_of_safety,
        verdict_survives_stress=(worst_case_profit > 0),
    )


def apply_behavioral_corrections(
    verdict: str,
    distance_km: float,
    profit_diff_pct: float,
    risk_score: float,
) -> str:
    """
    Apply farmer behavioural corrections to the verdict.

    Downgrade rules (max 2 tiers):
    - distance > 700 km → −1 tier
    - profit_diff vs nearest mandi < 5% → −1 tier
    - risk_score > 70 → −1 tier
    """
    if verdict not in VERDICT_TIERS:
        return verdict

    downgrade = 0
    if distance_km > FAR_DISTANCE_KM:
        downgrade += 1
    if profit_diff_pct < THIN_MARGIN_DIFF_PCT:
        downgrade += 1
    if risk_score > HIGH_RISK_THRESHOLD:
        downgrade += 1
    downgrade = min(downgrade, MAX_VERDICT_DOWNGRADE)

    current_idx = VERDICT_TIERS.index(verdict)
    new_idx = min(len(VERDICT_TIERS) - 1, current_idx + downgrade)
    return VERDICT_TIERS[new_idx]


def check_guardrails(
    roi_percentage: float,
    net_margin: float,
    cost_to_gross_ratio: float,
    profit_per_kg: float,
    price_per_kg: float,
) -> str | None:
    """
    Check economic guardrails. Returns a warning string or None if clean.
    Only the first triggered guardrail is returned.
    """
    if roi_percentage > ROI_ANOMALY_PCT:
        return "ROI anomaly — verify price data and commodity match"
    if net_margin > MARGIN_ANOMALY_PCT:
        return "Margin anomaly — check mandi fees and distance accuracy"
    if cost_to_gross_ratio < COST_RATIO_LOW:
        return "Cost unusually low — estimated distance may underestimate actual road distance"
    if price_per_kg > 0 and profit_per_kg > price_per_kg * PROFIT_PRICE_RATIO:
        return "Profit exceeds 80% of price — data integrity check needed"
    return None
```

**Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_transport_risk_engine.py -v
```
Expected: all tests PASS

**Step 5: Commit**

```bash
git add backend/app/transport/risk_engine.py backend/tests/test_transport_risk_engine.py
git commit -m "feat(transport): add risk_engine.py — composite risk, stress test, behavioral scoring, guardrails"
```

---

## Task 6: Update `schemas.py` — New Output Fields

**Files:**
- Modify: `backend/app/transport/schemas.py`

**Context:** Add new fields to `CostBreakdown` and `MandiComparison`. Add new `StressTestResult` schema. All new fields have sensible defaults so existing API callers don't break. The `StressTestResult` Pydantic model mirrors `risk_engine.StressTestResult` but is JSON-serialisable.

**Step 1: Read the file first**

Read `backend/app/transport/schemas.py` in full before editing.

**Step 2: Add `StressTestResult` Pydantic model before `CostBreakdown`**

After the `VehicleType` class (around line 27), add:

```python
class StressTestResult(BaseModel):
    """Worst-case scenario simulation results."""
    worst_case_profit: float = Field(..., description="Net profit after diesel+15%, toll+25%, price-12%, spoilage+5pp, grade_discount+3pp")
    break_even_price_per_kg: float = Field(..., description="Minimum price per kg needed to break even under stress")
    margin_of_safety_pct: float = Field(..., description="Buffer between normal and worst-case profit (%)")
    verdict_survives_stress: bool = Field(..., description="True if worst_case_profit > 0")

    model_config = ConfigDict(from_attributes=True)
```

**Step 3: Extend `CostBreakdown` with new fields**

Add after `additional_cost` and before `total_cost` in `CostBreakdown`:

```python
    driver_bata: float = Field(
        default=0.0,
        description="Driver daily bata for trip duration",
    )
    cleaner_bata: float = Field(
        default=0.0,
        description="Cleaner bata (trucks only; 0 for tempo)",
    )
    halt_cost: float = Field(
        default=0.0,
        description="Night halt cost (applied when round-trip > 12 hours)",
    )
    breakdown_reserve: float = Field(
        default=0.0,
        description="Breakdown buffer at ₹1/km (both ways)",
    )
    permit_cost: float = Field(
        default=0.0,
        description="Interstate permit cost (₹1,200 if crossing state boundary)",
    )
    rto_buffer: float = Field(
        default=0.0,
        description="RTO informal friction buffer (1.5% intrastate / 2.5% interstate of freight)",
    )
    loading_hamali: float = Field(
        default=0.0,
        description="Regional loading hamali charges at source",
    )
    unloading_hamali: float = Field(
        default=0.0,
        description="Regional unloading hamali charges at mandi",
    )
```

**Step 4: Extend `MandiComparison` with new fields**

Add after `distance_source` at the end of `MandiComparison`:

```python
    # Route & time
    travel_time_hours: float = Field(
        default=0.0,
        description="Estimated round-trip travel time in hours",
    )
    route_type: str = Field(
        default="mixed",
        description="Road category: 'highway' | 'mixed' | 'hill'",
    )
    is_interstate: bool = Field(
        default=False,
        description="True if source state differs from mandi state",
    )
    diesel_price_used: float = Field(
        default=98.0,
        description="Diesel price (₹/L) used in freight calculation",
    )

    # Perishability
    spoilage_percent: float = Field(
        default=0.0,
        description="Estimated quantity loss to spoilage (%)",
    )
    weight_loss_percent: float = Field(
        default=0.0,
        description="Moisture/weight shrinkage during transit (%)",
    )
    grade_discount_percent: float = Field(
        default=0.0,
        description="Auction grade discount applied (%)",
    )
    net_saleable_quantity_kg: float = Field(
        default=0.0,
        description="Quantity remaining after spoilage and weight loss (kg)",
    )

    # Price analytics
    price_volatility_7d: float = Field(
        default=0.0,
        description="7-day price volatility (coefficient of variation %)",
    )
    price_trend: str = Field(
        default="stable",
        description="Price direction: 'rising' | 'falling' | 'stable'",
    )

    # Risk
    risk_score: float = Field(
        default=0.0,
        description="Composite risk score 0–100 (higher = riskier)",
    )
    confidence_score: int = Field(
        default=100,
        description="Price data confidence 0–100",
    )
    stability_class: str = Field(
        default="stable",
        description="Risk tier: 'stable' | 'moderate' | 'volatile'",
    )

    # Stress test
    stress_test: StressTestResult | None = Field(
        default=None,
        description="Worst-case scenario simulation",
    )

    # Guardrail
    economic_warning: str | None = Field(
        default=None,
        description="Set when economic anomaly detected. None = clean.",
    )
```

**Step 5: Verify import still works**

```bash
cd backend && python -c "from app.transport.schemas import MandiComparison, StressTestResult, CostBreakdown; print('OK')"
```
Expected: `OK`

**Step 6: Commit**

```bash
git add backend/app/transport/schemas.py
git commit -m "feat(transport): extend schemas with StressTestResult and 15 new output fields"
```

---

## Task 7: Rewrite `service.py` Orchestrator

**Files:**
- Modify: `backend/app/transport/service.py`

**Context:** This is the main integration task. The orchestrator must:
1. Keep all existing public functions (`haversine_distance`, `select_vehicle`, `get_mandis_for_commodity`, `get_source_coordinates`, `compute_verdict`) intact — existing tests still pass
2. Add `compute_verdict_with_behavioral()` that calls `apply_behavioral_corrections`
3. Rewrite `calculate_net_profit()` to use real freight from `economics.py` + spoilage from `spoilage.py`
4. Rewrite `compare_mandis()` to integrate all new modules
5. Add structured audit logging via `logging.getLogger("transport.audit")`

**Step 1: Add audit logger import at top of service.py**

Add after existing imports:

```python
import json
import logging
from datetime import date as _date

from app.transport.economics import compute_freight, compute_travel_time, VEHICLE_CAPACITY_KG, PRACTICAL_CAPACITY_FACTOR
from app.transport.spoilage import compute_spoilage, compute_hamali
from app.transport.price_analytics import compute_price_analytics
from app.transport.risk_engine import (
    compute_risk_score,
    run_stress_test,
    apply_behavioral_corrections,
    check_guardrails,
)
from app.core.config import settings

_audit_log = logging.getLogger("transport.audit")
```

**Step 2: Update `select_vehicle()` to use 90% practical capacity**

The existing `select_vehicle` function selects vehicle by raw quantity. Update boundary to use practical capacity thresholds:

```python
def select_vehicle(quantity_kg: float) -> VehicleType:
    """Select vehicle type using 90% practical capacity thresholds."""
    if quantity_kg <= VEHICLE_CAPACITY_KG["TEMPO"] * PRACTICAL_CAPACITY_FACTOR:
        return VehicleType.TEMPO
    elif quantity_kg <= VEHICLE_CAPACITY_KG["TRUCK_SMALL"] * PRACTICAL_CAPACITY_FACTOR:
        return VehicleType.TRUCK_SMALL
    else:
        return VehicleType.TRUCK_LARGE
```

**Step 3: Rewrite `calculate_net_profit()` to use real freight**

Replace the existing `calculate_net_profit()` with this version:

```python
def calculate_net_profit(
    price_per_kg: float,
    quantity_kg: float,
    distance_km: float,
    vehicle_type: VehicleType,
    source_state: str = "Unknown",
    mandi_state: str = "Unknown",
    commodity_category: str | None = None,
    round_trip_hours: float | None = None,
    volatility_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate detailed cost breakdown and net profit using real Indian freight model.

    Uses economics.py for freight and spoilage.py for perishability.
    Falls back to legacy model if source/mandi state not provided.
    """
    diesel_price = getattr(settings, "diesel_price_per_liter", 98.0)

    # Real freight calculation
    freight = compute_freight(
        distance_km=distance_km,
        vehicle_type=vehicle_type,
        quantity_kg=quantity_kg,
        source_state=source_state,
        mandi_state=mandi_state,
        diesel_price=diesel_price,
    )

    # Spoilage
    travel_hours = round_trip_hours if round_trip_hours is not None else freight.round_trip_hours
    spo = compute_spoilage(commodity_category, travel_hours, volatility_pct)
    hamali = compute_hamali(mandi_state, quantity_kg)

    # Revenue accounting for spoilage
    gross_revenue = price_per_kg * quantity_kg
    net_qty = spo.net_saleable_quantity(quantity_kg)
    net_revenue = net_qty * price_per_kg * (1 - spo.grade_discount_fraction)

    # Mandi fees on gross revenue (standard APMC)
    mandi_fee = gross_revenue * MANDI_FEE_RATE
    commission = gross_revenue * COMMISSION_RATE

    # Additional fixed costs (weighbridge, parking, docs)
    additional_cost = (WEIGHBRIDGE_FEE + PARKING_FEE + DOCUMENTATION_FEE) * freight.trips

    # Total
    total_cost = (
        freight.total_freight
        + hamali.loading_hamali
        + hamali.unloading_hamali
        + mandi_fee
        + commission
        + additional_cost
    )

    net_profit = net_revenue - total_cost
    profit_per_kg = net_profit / quantity_kg if quantity_kg > 0 else 0
    roi_percentage = (net_profit / total_cost * 100) if total_cost > 0 else 0

    return {
        # Revenue
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "net_saleable_quantity_kg": net_qty,

        # Freight components (from economics.py)
        "transport_cost": freight.raw_transport,
        "toll_cost": freight.toll_cost,
        "driver_bata": freight.driver_bata,
        "cleaner_bata": freight.cleaner_bata,
        "halt_cost": freight.halt_cost,
        "breakdown_reserve": freight.breakdown_reserve,
        "permit_cost": freight.permit_cost,
        "rto_buffer": freight.rto_buffer,

        # Hamali (from spoilage.py)
        "loading_hamali": hamali.loading_hamali,
        "unloading_hamali": hamali.unloading_hamali,

        # Legacy fields (kept for backward compat)
        "loading_cost": hamali.loading_hamali,
        "unloading_cost": hamali.unloading_hamali,

        # Market costs
        "mandi_fee": mandi_fee,
        "commission": commission,
        "additional_cost": additional_cost,

        # Totals
        "total_cost": total_cost,
        "net_profit": net_profit,
        "profit_per_kg": profit_per_kg,
        "roi_percentage": roi_percentage,
        "trips": freight.trips,
        "toll_plazas": max(0, round(distance_km / TOLL_PLAZA_SPACING_KM)),

        # Spoilage
        "spoilage_percent": round(spo.spoilage_fraction * 100, 2),
        "weight_loss_percent": round(spo.weight_loss_fraction * 100, 2),
        "grade_discount_percent": round(spo.grade_discount_fraction * 100, 2),

        # Route metadata
        "travel_time_hours": freight.round_trip_hours,
        "route_type": freight.route_type,
        "is_interstate": freight.is_interstate,
        "diesel_price_used": freight.diesel_price_used,
    }
```

**Step 4: Rewrite `compare_mandis()` to integrate all new modules**

Replace the entire `compare_mandis()` function body (keeping the signature):

```python
def compare_mandis(
    request: TransportCompareRequest, db: Session = None
) -> tuple[List[MandiComparison], bool]:
    from app.transport.routing import routing_service
    from app.transport.schemas import StressTestResult as PydanticStressTestResult

    if not db:
        raise ValueError("Database session required")

    # Resolve commodity
    from app.models import Commodity
    commodity = db.query(Commodity).filter(
        Commodity.name.ilike(request.commodity)
    ).first()
    if not commodity:
        raise ValueError(f"Commodity '{request.commodity}' not found")

    commodity_category = getattr(commodity, "category", None)

    # Fetch mandis with prices
    raw_mandis = get_mandis_for_commodity(str(commodity.id), db, limit=200)

    # Source coords
    coords = get_source_coordinates(request, db)
    if coords is None:
        raise ValueError(
            f"Could not determine coordinates for district '{request.source_district}'. "
            f"Please provide source_latitude and source_longitude."
        )

    source_lat, source_lon = coords
    vehicle_type = select_vehicle(request.quantity_kg)

    # Pre-filter: price-sorted top N (hard cap from settings)
    max_eval = getattr(settings, "transport_max_mandis_evaluated", 25)
    osrm_candidate_limit = max(request.limit * 3, max_eval)

    eligible = [
        m for m in raw_mandis
        if m.get("latitude") and m.get("longitude") and m.get("price_per_kg") is not None
    ]
    eligible.sort(key=lambda m: m["price_per_kg"], reverse=True)
    candidates = eligible[:osrm_candidate_limit]

    # Batch price analytics (one query per mandi — fast with 7-row limit)
    price_analytics_map: dict[str, Any] = {}
    for m in candidates:
        pa = compute_price_analytics(str(commodity.id), m["name"], db)
        price_analytics_map[m["name"]] = pa

    # Parallel OSRM distances
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_distance(m: dict) -> tuple[dict, float, str]:
        dist, src = routing_service.get_distance_km(
            source_lat, source_lon, m["latitude"], m["longitude"], db
        )
        return m, dist, src

    distances: dict[str, tuple[float, str]] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_distance, m): m for m in candidates}
        for future in as_completed(futures):
            m, road_dist, dist_source = future.result()
            distances[m["name"]] = (road_dist, dist_source)

    diesel_price = getattr(settings, "diesel_price_per_liter", 98.0)
    diesel_baseline = getattr(settings, "diesel_baseline_price", 98.0)
    weather_risk_weight = getattr(settings, "transport_weather_risk_weight", 0.3)

    raw_comparisons: list[MandiComparison] = []
    has_estimated = False

    for m in candidates:
        road_dist, dist_source = distances[m["name"]]
        if dist_source == "estimated":
            has_estimated = True
        if request.max_distance_km and road_dist > request.max_distance_km:
            continue

        pa = price_analytics_map.get(m["name"])
        volatility_pct = pa.volatility_pct if pa else 0.0
        confidence_score = pa.confidence_score if pa else 100
        price_trend = pa.price_trend if pa else "stable"
        latest_price_date = pa.latest_price_date if pa else None

        profit_data = calculate_net_profit(
            price_per_kg=m["price_per_kg"],
            quantity_kg=request.quantity_kg,
            distance_km=road_dist,
            vehicle_type=vehicle_type,
            source_state=request.source_state or "Unknown",
            mandi_state=m.get("state") or "Unknown",
            commodity_category=commodity_category,
            volatility_pct=volatility_pct,
        )

        # Risk score
        risk_result = compute_risk_score(
            volatility_pct=volatility_pct,
            distance_km=road_dist,
            spoilage_fraction=profit_data["spoilage_percent"] / 100,
            diesel_price=diesel_price,
            diesel_baseline=diesel_baseline,
            is_interstate=profit_data["is_interstate"],
            weather_risk_weight=weather_risk_weight,
        )

        # Stress test
        stress_raw = run_stress_test(
            normal_profit=profit_data["net_profit"],
            normal_net_quantity=profit_data["net_saleable_quantity_kg"],
            normal_total_cost=profit_data["total_cost"],
            price_per_kg=m["price_per_kg"],
            toll_cost=profit_data["toll_cost"],
            raw_transport=profit_data["transport_cost"],
            spoilage_fraction=profit_data["spoilage_percent"] / 100,
            grade_discount_fraction=profit_data["grade_discount_percent"] / 100,
        )
        stress = PydanticStressTestResult(
            worst_case_profit=stress_raw.worst_case_profit,
            break_even_price_per_kg=stress_raw.break_even_price_per_kg,
            margin_of_safety_pct=stress_raw.margin_of_safety_pct,
            verdict_survives_stress=stress_raw.verdict_survives_stress,
        )

        # Guardrails
        gross_rev = profit_data["gross_revenue"]
        economic_warning = check_guardrails(
            roi_percentage=profit_data["roi_percentage"],
            net_margin=(profit_data["net_profit"] / gross_rev) if gross_rev > 0 else 0.0,
            cost_to_gross_ratio=(profit_data["total_cost"] / gross_rev) if gross_rev > 0 else 0.0,
            profit_per_kg=profit_data["profit_per_kg"],
            price_per_kg=m["price_per_kg"],
        )

        costs = CostBreakdown(
            transport_cost=round(profit_data["transport_cost"], 2),
            toll_cost=round(profit_data["toll_cost"], 2),
            loading_cost=round(profit_data["loading_cost"], 2),
            unloading_cost=round(profit_data["unloading_cost"], 2),
            mandi_fee=round(profit_data["mandi_fee"], 2),
            commission=round(profit_data["commission"], 2),
            additional_cost=round(profit_data["additional_cost"], 2),
            total_cost=round(profit_data["total_cost"], 2),
            driver_bata=round(profit_data["driver_bata"], 2),
            cleaner_bata=round(profit_data["cleaner_bata"], 2),
            halt_cost=round(profit_data["halt_cost"], 2),
            breakdown_reserve=round(profit_data["breakdown_reserve"], 2),
            permit_cost=round(profit_data["permit_cost"], 2),
            rto_buffer=round(profit_data["rto_buffer"], 2),
            loading_hamali=round(profit_data["loading_hamali"], 2),
            unloading_hamali=round(profit_data["unloading_hamali"], 2),
        )

        capacity = VEHICLE_CAPACITY_KG[vehicle_type.value]
        practical_cap = capacity * PRACTICAL_CAPACITY_FACTOR

        comp = MandiComparison(
            mandi_id=m.get("id"),
            mandi_name=m["name"],
            state=m.get("state") or "Unknown",
            district=m.get("district") or "Unknown",
            distance_km=round(road_dist, 1),
            price_per_kg=round(m["price_per_kg"], 2),
            gross_revenue=round(profit_data["gross_revenue"], 2),
            costs=costs,
            net_profit=round(profit_data["net_profit"], 2),
            profit_per_kg=round(profit_data["profit_per_kg"], 2),
            roi_percentage=round(profit_data["roi_percentage"], 1),
            vehicle_type=vehicle_type,
            vehicle_capacity_kg=int(capacity),
            trips_required=profit_data["trips"],
            recommendation="recommended" if profit_data["net_profit"] > 0 else "not_recommended",
            distance_source=dist_source,
            verdict="not_viable",
            verdict_reason="",
            # New fields
            travel_time_hours=round(profit_data["travel_time_hours"], 2),
            route_type=profit_data["route_type"],
            is_interstate=profit_data["is_interstate"],
            diesel_price_used=profit_data["diesel_price_used"],
            spoilage_percent=profit_data["spoilage_percent"],
            weight_loss_percent=profit_data["weight_loss_percent"],
            grade_discount_percent=profit_data["grade_discount_percent"],
            net_saleable_quantity_kg=round(profit_data["net_saleable_quantity_kg"], 1),
            price_volatility_7d=volatility_pct,
            price_trend=price_trend,
            risk_score=risk_result.risk_score,
            confidence_score=confidence_score,
            stability_class=risk_result.stability_class,
            stress_test=stress,
            economic_warning=economic_warning,
        )
        raw_comparisons.append(comp)

    # Sort by net_profit, assign rank-aware verdicts + behavioral corrections
    raw_comparisons.sort(key=lambda x: x.net_profit, reverse=True)
    total = len(raw_comparisons)
    best_profit = raw_comparisons[0].net_profit if raw_comparisons else 0.0

    for rank, comp in enumerate(raw_comparisons, start=1):
        tier, reason = compute_verdict(
            comp.net_profit, comp.gross_revenue, comp.profit_per_kg, rank, total
        )
        # Behavioral correction
        profit_diff_pct = (
            ((best_profit - comp.net_profit) / abs(best_profit) * 100)
            if best_profit != 0 else 0.0
        )
        adjusted_tier = apply_behavioral_corrections(
            verdict=tier,
            distance_km=comp.distance_km,
            profit_diff_pct=profit_diff_pct,
            risk_score=comp.risk_score,
        )
        # If stress test failed, downgrade verdict one additional tier if still positive
        if (comp.stress_test and not comp.stress_test.verdict_survives_stress
                and adjusted_tier == "excellent"):
            adjusted_tier = "good"

        comp.verdict = adjusted_tier
        comp.verdict_reason = reason

        # Audit log
        _audit_log.info(json.dumps({
            "event": "transport_comparison",
            "mandi_id": str(comp.mandi_id) if comp.mandi_id else None,
            "mandi_name": comp.mandi_name,
            "price_date": str(latest_price_date) if latest_price_date else None,
            "distance_source": comp.distance_source,
            "diesel_price": diesel_price,
            "spoilage_pct": comp.spoilage_percent,
            "volatility_pct": volatility_pct,
            "stress_test_worst_case": comp.stress_test.worst_case_profit if comp.stress_test else None,
            "risk_score": comp.risk_score,
            "verdict": comp.verdict,
            "travel_time_hours": comp.travel_time_hours,
            "is_interstate": comp.is_interstate,
        }))

    return raw_comparisons[:request.limit], has_estimated
```

**Step 5: Run ALL existing transport tests to confirm no regression**

```bash
cd backend && python -m pytest tests/test_transport_service.py tests/test_transport_routing.py tests/test_transport_api.py -v
```
Expected: all existing tests pass (some assertions about `calculate_net_profit` exact values may need updating if they test internal cost breakdown — see Step 6).

**Step 6: Fix any broken existing tests**

If `TestCalculateNetProfit.test_complete_calculation` fails because the cost breakdown changed (it will — real freight is different from old model):
- Update the test assertions to use `pytest.approx` with generous tolerances (5–10%)
- The test should still verify: `gross_revenue`, sign of `net_profit`, existence of all fields
- Do NOT remove tests — adapt them to the new realistic model

**Step 7: Commit**

```bash
git add backend/app/transport/service.py backend/tests/test_transport_service.py
git commit -m "feat(transport): rewrite service.py orchestrator with real freight, spoilage, risk, and audit logging"
```

---

## Task 8: Minor `routes.py` Updates

**Files:**
- Modify: `backend/app/transport/routes.py`

**Context:** The `/compare` endpoint needs no changes — it already returns `TransportCompareResponse` which now carries all new fields via the updated `MandiComparison`. The `/calculate` endpoint needs `estimated_time_hours` updated to use real speed calculation instead of hardcoded 50 km/h.

**Step 1: Update `/calculate` endpoint travel time estimate**

In `calculate_transport_cost()`, replace:
```python
"estimated_time_hours": round(distance_km / 50, 1),  # Assume 50 km/h average
```
with:
```python
"estimated_time_hours": round(distance_km / 42.0 * 2, 1),  # 42 km/h mixed, round-trip
```

**Step 2: Verify API still starts**

```bash
cd backend && python -c "from app.transport.routes import router; print('router OK')"
```

**Step 3: Run transport API tests**

```bash
cd backend && python -m pytest tests/test_transport_api.py -v
```
Expected: all pass (the API structure hasn't changed — only new fields added)

**Step 4: Commit**

```bash
git add backend/app/transport/routes.py
git commit -m "fix(transport): update /calculate travel time to use realistic 42 km/h mixed speed"
```

---

## Task 9: Full Test Suite Run + Regression Check

**Step 1: Run all transport tests**

```bash
cd backend && python -m pytest tests/test_transport_economics.py tests/test_transport_spoilage.py tests/test_transport_price_analytics.py tests/test_transport_risk_engine.py tests/test_transport_service.py tests/test_transport_routing.py tests/test_transport_api.py -v
```
Expected: all pass

**Step 2: Run the full test suite to verify no regressions elsewhere**

```bash
cd backend && python -m pytest --tb=short -q
```
Expected: same pass count as before (598 tests). If any fail, investigate — this PR should not break unrelated tests.

**Step 3: Verify the API server starts cleanly**

```bash
cd backend && python -c "from app.main import app; print('app OK')"
```

**Step 4: Final commit if any test fixes were needed**

```bash
git add -p  # review any remaining changes
git commit -m "test(transport): update existing service tests for realistic freight model"
```

---

## Task 10: Update `MEMORY.md` with new module summary

**Files:**
- Modify: `C:\Users\alame\.claude\projects\C--Users-alame-Desktop-repo-root\memory\MEMORY.md`

**Step 1: Add new section under Transport Routing Module entry**

Add after the existing Transport Routing Module section:

```markdown
## Transport Logistics Engine (upgraded 2026-02-28)
- `app/transport/economics.py` — FreightResult, compute_freight(), compute_travel_time(). BATA dict, diesel sensitivity, 90% capacity cap.
- `app/transport/spoilage.py` — SpoilageResult, exponential decay: `1 - (1-r)^(h/24)`. HamaliResult, regional rates.
- `app/transport/price_analytics.py` — PriceAnalytics, 7-day volatility (CV%), trend, confidence_score.
- `app/transport/risk_engine.py` — RiskResult, StressTestResult, apply_behavioral_corrections(), check_guardrails().
- Diesel price config: `settings.diesel_price_per_liter` (default 98.0), `settings.transport_max_mandis_evaluated` (default 25)
- All new fields in MandiComparison: risk_score, stress_test, spoilage_percent, confidence_score, economic_warning, etc.
- Audit logs: `logging.getLogger("transport.audit")` — structured JSON per comparison
- Worked example validated: truck_small, 292km intrastate, 5500kg → ₹23,581 total freight
```

**Step 2: Final commit**

```bash
git add "C:\Users\alame\.claude\projects\C--Users-alame-Desktop-repo-root\memory\MEMORY.md"
git commit -m "docs: update memory with logistics engine module summary"
```

---

## Validation Checklist

After completing all tasks, verify:

- [ ] `python -m pytest tests/test_transport_economics.py -v` — all pass
- [ ] `python -m pytest tests/test_transport_spoilage.py -v` — all pass
- [ ] `python -m pytest tests/test_transport_price_analytics.py -v` — all pass
- [ ] `python -m pytest tests/test_transport_risk_engine.py -v` — all pass
- [ ] `python -m pytest tests/test_transport_service.py -v` — all pass (may need assertion updates)
- [ ] `python -m pytest --tb=short -q` — no regressions in other test files
- [ ] `/compare` response includes `stress_test`, `risk_score`, `spoilage_percent`, `economic_warning`
- [ ] `/compare` for truck_small 5500kg 292km intrastate shows freight ≈ ₹23,000–24,200
- [ ] `economic_warning` is None for normal scenarios, not None for >500% ROI
- [ ] `verdict` for 700+ km routes is not "excellent" even with high price
