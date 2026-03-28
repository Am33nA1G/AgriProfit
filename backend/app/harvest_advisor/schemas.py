from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class WeatherWarning(BaseModel):
    warning_type: str   # "drought" | "flood" | "heat_stress" | "cold_stress" | "excess_rain"
    severity: str       # "low" | "medium" | "high" | "extreme"
    message: str
    source: str         # "historical" | "forecast" | "both"
    affected_period: str
    crop_impact: str


class CropRecommendation(BaseModel):
    crop_name: str
    rank: int
    gross_revenue_per_ha: float         # (yield_kg_ha / 100) × price_per_quintal
    input_cost_per_ha: float            # CACP Cost A2+FL estimate (₹/ha)
    expected_profit_per_ha: float       # gross_revenue - input_cost (net profit)
    expected_yield_kg_ha: float
    expected_price_per_quintal: float
    yield_confidence: str           # "high" | "medium" | "low"
    price_direction: str            # "up" | "flat" | "down"
    price_confidence_colour: str    # "Green" | "Yellow" | "Red"
    sowing_window: str
    harvest_window: str
    soil_suitability_note: Optional[str] = None
    has_market_data: bool = True


class HarvestAdvisorResponse(BaseModel):
    state: str
    district: str
    season: str
    recommendations: list[CropRecommendation]
    weather_warnings: list[WeatherWarning]
    rainfall_deficit_pct: Optional[float] = None
    drought_risk: Optional[str] = None   # "none"|"low"|"medium"|"high"|"extreme"
    soil_data_available: bool
    yield_data_available: bool
    forecast_available: bool
    disclaimer: str
    generated_at: str
    coverage_notes: list[str]
