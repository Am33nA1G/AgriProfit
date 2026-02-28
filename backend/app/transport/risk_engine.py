"""Risk scoring, stress testing, behavioral corrections, and economic guardrails."""
from __future__ import annotations
from dataclasses import dataclass

WEIGHT_VOLATILITY = 0.25; WEIGHT_DISTANCE = 0.20; WEIGHT_SPOILAGE = 0.20
WEIGHT_FUEL = 0.15; WEIGHT_REGULATORY = 0.10; WEIGHT_WEATHER = 0.10
VOLATILITY_NORM = 20.0; DISTANCE_NORM = 1000.0; SPOILAGE_NORM = 0.15; FUEL_NORM = 0.20
STABLE_THRESHOLD = 30.0; MODERATE_THRESHOLD = 60.0
STRESS_DIESEL_PCT = 0.15; STRESS_TOLL_PCT = 0.25; STRESS_PRICE_PCT = -0.12
STRESS_SPOILAGE_ADD = 0.05; STRESS_GRADE_ADD = 0.03
FAR_DISTANCE_KM = 700.0; THIN_MARGIN_DIFF_PCT = 5.0; HIGH_RISK_THRESHOLD = 70.0
MAX_VERDICT_DOWNGRADE = 2
VERDICT_TIERS = ["excellent", "good", "marginal", "not_viable"]
ROI_ANOMALY_PCT = 500.0; MARGIN_ANOMALY_PCT = 0.55; COST_RATIO_LOW = 0.06; PROFIT_PRICE_RATIO = 0.80


@dataclass
class RiskResult:
    risk_score: float
    confidence_score: int
    stability_class: str


@dataclass
class StressTestResult:
    worst_case_profit: float
    break_even_price_per_kg: float
    margin_of_safety_pct: float
    verdict_survives_stress: bool


def compute_risk_score(
    volatility_pct: float, distance_km: float, spoilage_fraction: float,
    diesel_price: float, diesel_baseline: float, is_interstate: bool,
    weather_risk_weight: float,
) -> RiskResult:
    fuel_delta = abs(diesel_price - diesel_baseline) / max(diesel_baseline, 1.0)
    raw = (
        min(1.0, volatility_pct / VOLATILITY_NORM) * WEIGHT_VOLATILITY
        + min(1.0, distance_km / DISTANCE_NORM) * WEIGHT_DISTANCE
        + min(1.0, spoilage_fraction / SPOILAGE_NORM) * WEIGHT_SPOILAGE
        + min(1.0, fuel_delta / FUEL_NORM) * WEIGHT_FUEL
        + (1.0 if is_interstate else 0.0) * WEIGHT_REGULATORY
        + min(1.0, weather_risk_weight) * WEIGHT_WEATHER
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
    normal_profit: float, normal_net_quantity: float, normal_total_cost: float,
    price_per_kg: float, toll_cost: float, raw_transport: float,
    spoilage_fraction: float, grade_discount_fraction: float,
) -> StressTestResult:
    stressed_price = price_per_kg * (1 + STRESS_PRICE_PCT)
    stressed_toll = toll_cost * (1 + STRESS_TOLL_PCT)
    stressed_transport = raw_transport * (1 + STRESS_DIESEL_PCT)
    stressed_spoilage = min(0.99, spoilage_fraction + STRESS_SPOILAGE_ADD)
    stressed_grade = min(0.99, grade_discount_fraction + STRESS_GRADE_ADD)
    quantity_base = normal_net_quantity / max(1e-9, (1 - spoilage_fraction))
    stressed_net_qty = quantity_base * (1 - stressed_spoilage)
    stressed_revenue = stressed_net_qty * stressed_price * (1 - stressed_grade)
    cost_adjustment = (stressed_toll - toll_cost) + (stressed_transport - raw_transport)
    stressed_total_cost = normal_total_cost + cost_adjustment
    worst_case_profit = round(stressed_revenue - stressed_total_cost, 2)
    break_even_price = round(stressed_total_cost / max(stressed_net_qty * (1 - stressed_grade), 1e-6), 2)
    margin_of_safety = round((normal_profit - worst_case_profit) / max(abs(normal_profit), 1.0) * 100, 1)
    return StressTestResult(
        worst_case_profit=worst_case_profit,
        break_even_price_per_kg=break_even_price,
        margin_of_safety_pct=margin_of_safety,
        verdict_survives_stress=(worst_case_profit > 0),
    )


def apply_behavioral_corrections(
    verdict: str, distance_km: float, profit_diff_pct: float, risk_score: float,
) -> str:
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
    return VERDICT_TIERS[min(len(VERDICT_TIERS) - 1, current_idx + downgrade)]


def check_guardrails(
    roi_percentage: float, net_margin: float, cost_to_gross_ratio: float,
    profit_per_kg: float, price_per_kg: float,
) -> str | None:
    if roi_percentage > ROI_ANOMALY_PCT:
        return "ROI anomaly — verify price data and commodity match"
    if net_margin > MARGIN_ANOMALY_PCT:
        return "Margin anomaly — check mandi fees and distance accuracy"
    if cost_to_gross_ratio < COST_RATIO_LOW:
        return "Cost unusually low — estimated distance may underestimate actual road distance"
    if price_per_kg > 0 and profit_per_kg > price_per_kg * PROFIT_PRICE_RATIO:
        return "Profit exceeds 80% of price — data integrity check needed"
    return None
