"""
Perishability model — exponential spoilage decay, weight loss, grade discount, hamali.

Formula: spoilage_fraction = 1 - (1 - rate_per_24h) ** (round_trip_hours / 24)
Rates from design doc (open-truck, no cold chain).
"""
from __future__ import annotations
from dataclasses import dataclass

SPOILAGE_RATES: dict[str, dict[str, float]] = {
    "vegetable": {"rate": 0.030,  "weight_loss": 0.025,  "grade_discount": 0.040},
    "fruit":     {"rate": 0.050,  "weight_loss": 0.020,  "grade_discount": 0.050},
    "spice":     {"rate": 0.003,  "weight_loss": 0.005,  "grade_discount": 0.010},
    "grain":     {"rate": 0.0015, "weight_loss": 0.0075, "grade_discount": 0.005},
    "paddy":     {"rate": 0.0015, "weight_loss": 0.0075, "grade_discount": 0.005},
    "pulses":    {"rate": 0.001,  "weight_loss": 0.005,  "grade_discount": 0.005},
    "unknown":   {"rate": 0.005,  "weight_loss": 0.0075, "grade_discount": 0.010},
}

AUCTION_UNDERBID_FRACTION: float = 0.015
HIGH_VOLATILITY_THRESHOLD: float = 8.0

NORTH_STATES = {
    "uttar pradesh", "punjab", "haryana", "bihar", "madhya pradesh",
    "rajasthan", "himachal pradesh", "uttarakhand", "delhi", "chandigarh",
}
SOUTH_STATES = {
    "kerala", "tamil nadu", "karnataka", "andhra pradesh", "telangana",
}
MAHA_STATES = {"maharashtra", "gujarat"}

HAMALI_RATES: dict[str, tuple[float, float]] = {
    "north":       (10.0, 12.0),
    "south":       (18.0, 22.0),
    "maharashtra": (13.0, 16.0),
    "default":     (15.0, 18.0),
}


@dataclass
class SpoilageResult:
    category: str
    spoilage_fraction: float
    weight_loss_fraction: float
    grade_discount_fraction: float

    def net_saleable_quantity(self, quantity_kg: float) -> float:
        return quantity_kg * (1 - self.spoilage_fraction) * (1 - self.weight_loss_fraction)

    def net_revenue(self, quantity_kg: float, price_per_kg: float) -> float:
        return self.net_saleable_quantity(quantity_kg) * price_per_kg * (1 - self.grade_discount_fraction)


@dataclass
class HamaliResult:
    mandi_state: str
    loading_hamali: float
    unloading_hamali: float
    total_hamali: float


def _normalize_category(category: str | None) -> str:
    if not category:
        return "unknown"
    return category.strip().lower()


def compute_spoilage(
    category: str | None,
    round_trip_hours: float,
    volatility_pct: float = 0.0,
) -> SpoilageResult:
    """Compute exponential spoilage fraction and related losses."""
    cat = _normalize_category(category)
    rates = SPOILAGE_RATES.get(cat, SPOILAGE_RATES["unknown"])
    r = rates["rate"]
    spoilage = 0.0 if round_trip_hours <= 0 else 1 - (1 - r) ** (round_trip_hours / 24)
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
    loading = round(quintals * load_rate, 2)
    unloading = round(quintals * unload_rate, 2)
    return HamaliResult(
        mandi_state=mandi_state,
        loading_hamali=loading,
        unloading_hamali=unloading,
        total_hamali=round(loading + unloading, 2),
    )
