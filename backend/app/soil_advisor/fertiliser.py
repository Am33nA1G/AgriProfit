"""Fertiliser advice pure functions.

Generates actionable fertiliser advice cards based on a block's soil nutrient
deficiency profile. pH is intentionally excluded from advice — pH management
requires on-site testing and is handled separately.
"""
from __future__ import annotations

# FERTILISER_ADVICE covers N, P, K, OC only.
# "Potential Of Hydrogen" is intentionally absent — pH is a range check, not a deficiency.
FERTILISER_ADVICE: dict[str, dict] = {
    "Nitrogen": {
        "message_template": "% of soils in this block are nitrogen-deficient — consider urea application before planting",
        "fertiliser": "Urea (46% N) at 120-150 kg/ha for cereals; 50-80 kg/ha for legumes",
    },
    "Phosphorus": {
        "message_template": "% of soils in this block are phosphorus-deficient — apply phosphatic fertiliser at sowing",
        "fertiliser": "DAP (18% N, 46% P2O5) at 100-125 kg/ha or SSP at 250-375 kg/ha",
    },
    "Potassium": {
        "message_template": "% of soils in this block are potassium-deficient — consider muriate of potash",
        "fertiliser": "MOP (60% K2O) at 50-100 kg/ha based on crop requirement",
    },
    "Organic Carbon": {
        "message_template": "% of soils in this block have low organic carbon — incorporate organic matter",
        "fertiliser": "FYM (farmyard manure) at 10-15 t/ha or compost at 5-7 t/ha",
    },
}


def generate_fertiliser_advice(profile: dict, threshold: int = 50) -> list[dict]:
    """Generate fertiliser advice cards for nutrients where low_pct exceeds threshold.

    Args:
        profile: Block nutrient profile dict of the form:
            {"Nitrogen": {"high": 0, "medium": 4, "low": 96}, ...}
        threshold: Deficiency threshold (default 50). Advice is generated only
            when low_pct > threshold (strict greater-than).

    Returns:
        List of advice card dicts. Each card has:
            - nutrient: str
            - low_pct: int
            - message: str (low_pct prepended to the message template)
            - fertiliser_recommendation: str
        Returns empty list when no nutrients exceed the threshold.
        pH ("Potential Of Hydrogen") is never included.
    """
    advice_cards = []
    for nutrient, template in FERTILISER_ADVICE.items():
        low_pct = profile.get(nutrient, {}).get("low", 0)
        if low_pct > threshold:
            advice_cards.append(
                {
                    "nutrient": nutrient,
                    "low_pct": low_pct,
                    "message": f"{low_pct}{template['message_template']}",
                    "fertiliser_recommendation": template["fertiliser"],
                }
            )
    return advice_cards
