"""Soil crop suitability pure functions.

All functions are stateless and database-free. They operate on plain dicts
representing a block's soil nutrient profile and crop_row records.

A block profile dict has the structure:
    {
        "Nitrogen": {"high": 4, "medium": 0, "low": 96},
        "Phosphorus": {"high": 20, "medium": 50, "low": 30},
        ...
    }

A crop_row dict (as returned from soil_crop_suitability table) has:
    {
        "crop_name": "Soybean",
        "nutrient": "Nitrogen",
        "min_tolerance": "low",   # "low" | "medium" | "high"
        "ph_min": 6.0,
        "ph_max": 7.0,
    }
"""
from __future__ import annotations

COVERED_STATES: frozenset[str] = frozenset(
    {
        "ANDHRA PRADESH",
        "ARUNACHAL PRADESH",
        "ASSAM",
        "BIHAR",
        "CHHATTISGARH",
        "GOA",
        "GUJARAT",
        "HARYANA",
        "HIMACHAL PRADESH",
        "JAMMU & KASHMIR",
        "JHARKHAND",
        "KARNATAKA",
        "KERALA",
        "LADAKH",
        "MADHYA PRADESH",
        "MAHARASHTRA",
        "MANIPUR",
        "MEGHALAYA",
        "MIZORAM",
        "NAGALAND",
        "ANDAMAN & NICOBAR",
    }
)

# Threshold: blocks where low_pct exceeds this value are considered deficient
DEFICIENCY_THRESHOLD: int = 50

# Ordering of tolerance levels (lower index = more tolerant of poor soil)
LEVEL_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

# ICAR crop-to-tolerance thresholds (for reference and seeding; rank_crops uses crop_rows from DB)
ICAR_THRESHOLDS: dict[str, dict] = {
    "Rice":      {"N_min": "medium", "P_min": "low",    "K_min": "medium", "ph_min": 5.5, "ph_max": 7.0},
    "Wheat":     {"N_min": "high",   "P_min": "medium", "K_min": "medium", "ph_min": 6.0, "ph_max": 7.5},
    "Maize":     {"N_min": "high",   "P_min": "medium", "K_min": "medium", "ph_min": 5.5, "ph_max": 7.0},
    "Soybean":   {"N_min": "low",    "P_min": "medium", "K_min": "medium", "ph_min": 6.0, "ph_max": 7.0},
    "Groundnut": {"N_min": "low",    "P_min": "medium", "K_min": "medium", "ph_min": 5.5, "ph_max": 7.0},
    "Cotton":    {"N_min": "high",   "P_min": "medium", "K_min": "high",   "ph_min": 6.0, "ph_max": 7.5},
    "Sugarcane": {"N_min": "high",   "P_min": "medium", "K_min": "high",   "ph_min": 6.0, "ph_max": 7.5},
    "Potato":    {"N_min": "medium", "P_min": "medium", "K_min": "high",   "ph_min": 5.0, "ph_max": 6.5},
    "Tomato":    {"N_min": "medium", "P_min": "medium", "K_min": "high",   "ph_min": 5.5, "ph_max": 7.0},
    "Onion":     {"N_min": "medium", "P_min": "high",   "K_min": "high",   "ph_min": 6.0, "ph_max": 7.5},
    "Chickpea":  {"N_min": "low",    "P_min": "medium", "K_min": "medium", "ph_min": 6.0, "ph_max": 7.5},
    "Mustard":   {"N_min": "medium", "P_min": "medium", "K_min": "medium", "ph_min": 5.5, "ph_max": 7.0},
    "Bajra":     {"N_min": "medium", "P_min": "low",    "K_min": "low",    "ph_min": 6.0, "ph_max": 7.5},
    "Jowar":     {"N_min": "medium", "P_min": "low",    "K_min": "low",    "ph_min": 6.0, "ph_max": 8.0},
    "Lentil":    {"N_min": "low",    "P_min": "medium", "K_min": "medium", "ph_min": 6.0, "ph_max": 7.5},
}


def is_deficient(profile: dict, nutrient: str) -> bool:
    """Return True if more than 50% of the block's soils are low in this nutrient.

    Args:
        profile: Block nutrient profile dict.
        nutrient: Nutrient name (e.g., "Nitrogen").

    Returns:
        True when profile[nutrient]["low"] > DEFICIENCY_THRESHOLD.
    """
    low_pct = profile.get(nutrient, {}).get("low", 0)
    return low_pct > DEFICIENCY_THRESHOLD


def score_crop(profile: dict, tolerances: dict) -> float:
    """Score a single crop_row against a block profile for its specific nutrient.

    Scoring rationale:
    - A crop with min_tolerance="low" thrives even when soils are poor
      (high low_pct is acceptable) — it gets a high base score.
    - A crop with min_tolerance="medium" needs moderate soil; it scores 0
      when the block is deficient in that nutrient.
    - A crop with min_tolerance="high" requires rich soil; it scores 0
      when the block is deficient.

    Args:
        profile: Block nutrient profile dict.
        tolerances: A single crop_row dict with keys:
            crop_name, nutrient, min_tolerance, ph_min, ph_max.

    Returns:
        Float score >= 0.0. Higher is better. 0.0 means crop is unsuitable.
    """
    nutrient = tolerances["nutrient"]
    min_tol = tolerances["min_tolerance"]
    tolerance_level = LEVEL_ORDER.get(min_tol, 1)

    block_low_pct = profile.get(nutrient, {}).get("low", 0)
    block_medium_pct = profile.get(nutrient, {}).get("medium", 0)

    if tolerance_level == 0:
        # low tolerance: crop handles poor soil well — reward both low and medium
        return (block_low_pct + block_medium_pct) / 100.0 + 1.0

    if tolerance_level == 1:
        # medium tolerance: penalise deficient blocks
        if is_deficient(profile, nutrient):
            return 0.0
        return block_medium_pct / 100.0 + 0.5

    # tolerance_level == 2 (high): zero score for deficient blocks
    if is_deficient(profile, nutrient):
        return 0.0
    return block_medium_pct / 100.0


def rank_crops(profile: dict, crop_rows: list[dict]) -> list[dict]:
    """Rank crops by suitability for the given block soil profile.

    Aggregates per-nutrient scores by crop name so each crop appears exactly
    once in the result (sum of scores across all its nutrient rows).

    Args:
        profile: Block nutrient profile dict.
        crop_rows: List of crop_row dicts (one row per crop-nutrient combination).

    Returns:
        Up to 5 dicts with keys crop_name, total_score, sorted by total_score
        descending. Crops whose total score is 0 are excluded.
    """
    totals: dict[str, float] = {}
    for row in crop_rows:
        s = score_crop(profile, row)
        name = row["crop_name"]
        totals[name] = totals.get(name, 0.0) + s

    ranked = [
        {"crop_name": name, "score": total}
        for name, total in totals.items()
        if total > 0
    ]
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:5]
