"""Soil Advisor service layer.

Queries the soil_profiles and soil_crop_suitability tables and integrates
with the pure suitability/fertiliser functions to produce SoilAdvisorResponse.

All DB calls use sync SQLAlchemy (Session). No async handlers.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.soil_advisor.fertiliser import generate_fertiliser_advice
from app.soil_advisor.schemas import (
    CropRecommendation,
    FertiliserAdvice,
    NutrientDistribution,
    SoilAdvisorResponse,
)
from app.soil_advisor.suitability import COVERED_STATES, rank_crops
from app.ml.soil_suitability_loader import predict_crop_suitability

logger = logging.getLogger(__name__)

# Canonical ordering of the 5 nutrients stored in soil_profiles
NUTRIENT_ORDER = [
    "Nitrogen",
    "Phosphorus",
    "Potassium",
    "Organic Carbon",
    "Potential Of Hydrogen",
]


def get_states(db: Session) -> list[str]:  # noqa: ARG001
    """Return sorted list of covered state names.

    The authoritative source is COVERED_STATES (the suitability module)
    — no DB query required.
    """
    return sorted(COVERED_STATES)


def get_districts_for_state(db: Session, state: str) -> list[str]:
    """Return distinct districts for the given state, sorted alphabetically."""
    rows = db.execute(
        text(
            "SELECT DISTINCT district FROM soil_profiles "
            "WHERE state = :state ORDER BY district"
        ),
        {"state": state.upper().strip()},
    ).fetchall()
    return [r[0] for r in rows]


def get_blocks_for_district(db: Session, state: str, district: str) -> list[str]:
    """Return distinct blocks for the given state + district, sorted alphabetically."""
    rows = db.execute(
        text(
            "SELECT DISTINCT block FROM soil_profiles "
            "WHERE state = :state AND district = :district ORDER BY block"
        ),
        {"state": state.upper().strip(), "district": district.upper().strip()},
    ).fetchall()
    return [r[0] for r in rows]


def get_block_profile(
    db: Session, state: str, district: str, block: str
) -> dict | None:
    """Query the most recent cycle's nutrient data for a block.

    Returns a profile dict with the structure expected by rank_crops/
    generate_fertiliser_advice, or None if no rows are found.

    Example output:
        {
            "cycle": "2025-26",
            "block_name": "ANANTAPUR - 4689",
            "Nitrogen": {"high": 0, "medium": 4, "low": 96},
            "Phosphorus": {"high": 81, "medium": 17, "low": 2},
            ...
        }
    """
    rows = db.execute(
        text(
            """
            SELECT nutrient, high_pct, medium_pct, low_pct, cycle
            FROM soil_profiles
            WHERE state = :state
              AND district = :district
              AND block = :block
              AND cycle = (
                  SELECT MAX(cycle)
                  FROM soil_profiles
                  WHERE state = :state
                    AND district = :district
                    AND block = :block
              )
            """
        ),
        {
            "state": state,
            "district": district,
            "block": block,
        },
    ).fetchall()

    if not rows:
        return None

    profile: dict = {
        "cycle": rows[0][4],
        "block_name": block,
    }
    for row in rows:
        nutrient, high_pct, medium_pct, low_pct, _cycle = row
        profile[nutrient] = {
            "high": int(high_pct),
            "medium": int(medium_pct),
            "low": int(low_pct),
        }
    return profile


def _get_seasonal_demand(
    db: Session, crop_name: str, state: str
) -> str | None:
    """Query seasonal_price_stats for demand signal. Returns None on any error."""
    try:
        row = db.execute(
            text(
                """
                SELECT MAX(best_sell_month) as demand_signal
                FROM seasonal_price_stats
                WHERE commodity_name ILIKE :crop_name AND state = :state
                LIMIT 1
                """
            ),
            {"crop_name": crop_name, "state": state},
        ).fetchone()
        if row and row[0] is not None:
            return str(row[0])
        return None
    except (OperationalError, Exception):  # Table may not exist yet (Phase 2 dependency)
        return None


def get_soil_advice(
    db: Session, state: str, district: str, block: str
) -> SoilAdvisorResponse:
    """Orchestrate the soil advisor response for a state/district/block.

    Steps:
    1. Fetch block profile (most recent cycle).
    2. Rank crops using ICAR suitability logic.
    3. Build nutrient distributions.
    4. Generate fertiliser advice cards.
    5. Attempt seasonal demand enrichment (optional, never raises).
    6. Return SoilAdvisorResponse.

    Raises:
        HTTPException 404: If no soil data exists for the given block.
    """
    state_upper = state.upper().strip()
    district_upper = district.upper().strip()

    profile = get_block_profile(db, state_upper, district_upper, block)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"No soil data found for block '{block}' in {district}, {state}.",
        )

    # --- Crop ranking: ML model first, rule-based fallback ---
    ml_crops = predict_crop_suitability(profile, state_upper)
    if ml_crops:
        ranked = ml_crops
    else:
        crop_rows = db.execute(
            text("SELECT crop_name, nutrient, min_tolerance, ph_min, ph_max FROM soil_crop_suitability")
        ).fetchall()
        crop_dicts = [dict(r._mapping) for r in crop_rows]
        ranked = rank_crops(profile, crop_dicts)

    # --- Nutrient distributions (fixed 5-nutrient order) ---
    nutrient_distributions = []
    for nutrient in NUTRIENT_ORDER:
        nd = profile.get(nutrient, {"high": 0, "medium": 0, "low": 0})
        nutrient_distributions.append(
            NutrientDistribution(
                nutrient=nutrient,
                high_pct=nd["high"],
                medium_pct=nd["medium"],
                low_pct=nd["low"],
            )
        )

    # --- Fertiliser advice ---
    raw_advice = generate_fertiliser_advice(profile)
    fertiliser_advice = [
        FertiliserAdvice(
            nutrient=a["nutrient"],
            low_pct=a["low_pct"],
            message=a["message"],
            fertiliser_recommendation=a["fertiliser_recommendation"],
        )
        for a in raw_advice
    ]

    # --- Crop recommendations with optional seasonal demand ---
    crop_recommendations = []
    for rank_idx, crop_row in enumerate(ranked, start=1):
        seasonal_demand = _get_seasonal_demand(db, crop_row["crop_name"], state_upper)
        crop_recommendations.append(
            CropRecommendation(
                crop_name=crop_row["crop_name"],
                suitability_score=round(crop_row["score"], 4),
                suitability_rank=rank_idx,
                seasonal_demand=seasonal_demand,
            )
        )

    return SoilAdvisorResponse(
        state=state_upper,
        district=district_upper,
        block=block,
        cycle=profile["cycle"],
        disclaimer=f"Block-average soil data for {block} — not field-level measurement",
        nutrient_distributions=nutrient_distributions,
        crop_recommendations=crop_recommendations,
        fertiliser_advice=fertiliser_advice,
        coverage_gap=False,
    )
