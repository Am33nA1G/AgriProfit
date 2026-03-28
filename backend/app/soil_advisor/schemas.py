"""Pydantic schemas for the Soil Advisor API responses.

These schemas define the shape of data returned by the
/api/v1/soil-advisor/* endpoints.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class NutrientDistribution(BaseModel):
    """Distribution of soil nutrient levels across a block."""

    model_config = ConfigDict(from_attributes=True)

    nutrient: str
    high_pct: int
    medium_pct: int
    low_pct: int


class CropRecommendation(BaseModel):
    """A single crop recommended for the block's soil conditions."""

    model_config = ConfigDict(from_attributes=True)

    crop_name: str
    suitability_score: float
    suitability_rank: int
    seasonal_demand: Optional[str] = None  # 'HIGH' | 'MEDIUM' | 'LOW' | None


class FertiliserAdvice(BaseModel):
    """Actionable fertiliser advice for a deficient nutrient."""

    model_config = ConfigDict(from_attributes=True)

    nutrient: str
    low_pct: int
    message: str
    fertiliser_recommendation: str


class SoilAdvisorResponse(BaseModel):
    """Full soil advisor response for a state/district/block combination."""

    model_config = ConfigDict(from_attributes=True)

    state: str
    district: str
    block: str
    cycle: str
    # Always present: "Block-average soil data for {block} — not field-level measurement"
    disclaimer: str
    nutrient_distributions: list[NutrientDistribution]   # exactly 5 nutrients
    crop_recommendations: list[CropRecommendation]        # 3-5 crops
    fertiliser_advice: list[FertiliserAdvice]            # 0-4 advice cards
    coverage_gap: bool = False
