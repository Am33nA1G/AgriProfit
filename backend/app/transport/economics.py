"""
Real Indian freight cost calculation engine.

Validated against worked example (design doc):
  truck_small, 292 km intrastate, 5500 kg, diesel ₹98, 42 km/h → ₹23,581 total freight
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

DIESEL_BASELINE: float = 98.0
PRACTICAL_CAPACITY_FACTOR: float = 0.90
BREAKDOWN_RESERVE_PER_KM: float = 1.0
RTO_FRICTION_INTRASTATE: float = 0.015
RTO_FRICTION_INTERSTATE: float = 0.025
INTERSTATE_PERMIT_COST: float = 1200.0
TOLL_PLAZA_SPACING_KM: float = 70.0
WORKING_HOURS_PER_DAY: float = 10.0

SPEED_HIGHWAY: float = 55.0
SPEED_MIXED: float = 42.0
SPEED_HILL: float = 32.0
URBAN_CONGESTION_FACTOR: float = 1.15

HILL_STATES: frozenset[str] = frozenset({
    "jammu and kashmir", "himachal pradesh", "uttarakhand", "sikkim",
    "arunachal pradesh", "meghalaya", "nagaland", "manipur", "mizoram", "tripura",
})

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
# DATA CLASS
# =============================================================================

@dataclass
class FreightResult:
    vehicle_type: str
    trips: int
    round_trip_hours: float
    days: int
    is_interstate: bool
    route_type: str
    diesel_price_used: float
    raw_transport: float
    toll_cost: float
    driver_bata: float
    cleaner_bata: float
    halt_cost: float
    breakdown_reserve: float
    permit_cost: float
    rto_buffer: float
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
    """Return estimated round-trip travel time in hours."""
    if distance_km <= 0:
        return 0.0
    speed = SPEED_HILL if _is_hill_route(source_state, mandi_state) else SPEED_MIXED
    round_trip = distance_km / speed * 2
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
    """Compute full real-world freight cost breakdown."""
    vt = vehicle_type.value
    is_hill = _is_hill_route(source_state, mandi_state)
    route_type = "hill" if is_hill else "mixed"
    speed = SPEED_HILL if is_hill else SPEED_MIXED

    # Diesel-adjusted rate
    dependency = DIESEL_DEPENDENCY[vt]
    effective_rate = BASE_RATES[vt] * (
        1 + dependency * ((diesel_price - DIESEL_BASELINE) / DIESEL_BASELINE)
    )

    # Trips with 90% cap
    practical_capacity = VEHICLE_CAPACITY_KG[vt] * PRACTICAL_CAPACITY_FACTOR
    trips = math.ceil(quantity_kg / practical_capacity)

    raw_transport = round(distance_km * effective_rate * 2 * trips, 2)

    toll_plazas = max(0, round(distance_km / TOLL_PLAZA_SPACING_KM))
    toll_cost = round(toll_plazas * TOLL_PER_PLAZA[vt] * 2 * trips, 2)

    round_trip_hours = distance_km / speed * 2
    if urban:
        round_trip_hours *= URBAN_CONGESTION_FACTOR
    days = max(1, math.ceil(round_trip_hours / WORKING_HOURS_PER_DAY))

    driver_bata = round(BATA[vt]["driver_day"] * days, 2)
    cleaner_bata = round(BATA[vt]["cleaner_day"] * days, 2)
    halt_cost = BATA[vt]["night_halt"] if round_trip_hours > 12.0 else 0.0
    breakdown_reserve = round(BREAKDOWN_RESERVE_PER_KM * distance_km * 2, 2)

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
