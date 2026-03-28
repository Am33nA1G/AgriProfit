"""
Crop input cost estimates (₹ per hectare) based on CACP Cost A2+FL data.

Source: Commission for Agricultural Costs and Prices (CACP) annual reports 2023-24.
Cost A2+FL = actual paid-out costs (seed, fertilizer, pesticide, machinery, hired labour)
            + imputed value of family labour at prevailing market wage.

These are national averages — regional variation can be ±20%.
"""

CROP_INPUT_COSTS: dict[str, float] = {
    # ── Food Grains ────────────────────────────────────────────────────────────
    "rice":          28_000,   # seed 2K, fert 8K, pesticide 3K, machinery 5K, labour 10K
    "wheat":         25_000,   # seed 3K, fert 8K, pesticide 1K, machinery 6K, labour 7K
    "maize":         22_000,
    "jowar":         14_000,
    "bajra":         12_000,
    "barley":        18_000,
    "ragi":          16_000,

    # ── Pulses ─────────────────────────────────────────────────────────────────
    "arhar":         20_000,   # CACP 2022-23 est ₹19,500 – 21,000
    "moong":         18_000,
    "urad":          18_000,
    "chana":         22_000,
    "lentil":        19_000,

    # ── Oilseeds ───────────────────────────────────────────────────────────────
    "groundnut":     35_000,   # high labour for digging + picking
    "mustard":       22_000,
    "soybean":       24_000,
    "sunflower":     28_000,

    # ── Vegetables (high input intensity) ──────────────────────────────────────
    "tomato":        60_000,   # poly-mulch, staking, frequent pesticide sprays
    "onion":         55_000,
    "potato":        80_000,   # seed potato alone ₹20–25K/ha
    "brinjal":       40_000,
    "cauliflower":   45_000,
    "carrot":        35_000,

    # ── Fruits (annual maintenance cost for perennials) ────────────────────────
    "mango":         25_000,   # orchard maintenance, spray, harvest labour
    "banana":        90_000,   # planting material, propping, bunch cover, irrigation
    "grapes":       120_000,   # trellis maintenance, pruning labour, sprays
    "orange":        30_000,
    "pomegranate":   35_000,

    # ── Cash Crops ─────────────────────────────────────────────────────────────
    "cotton":        45_000,   # CACP 2022-23 actual est.
    "sugarcane":     80_000,   # planting material, irrigation-intensive
    "jute":          25_000,
    "coffee":        40_000,
}

# Default cost for crops not in the dictionary above (conservative average)
DEFAULT_INPUT_COST: float = 25_000


# ── Yield sanity bounds (kg/ha) ───────────────────────────────────────────────
# Source: ICAR crop production guides, CACP cost studies, ICRISAT VDSA data.
# Model predictions outside these bounds are physically impossible and are clamped.
# Tuple: (min_kg_ha, max_kg_ha)

CROP_YIELD_BOUNDS: dict[str, tuple[float, float]] = {
    # Food Grains
    "rice":         (500,    8_000),
    "wheat":        (800,    6_500),
    "maize":        (500,    7_000),
    "jowar":        (300,    4_000),
    "bajra":        (400,    3_500),
    "barley":       (800,    4_500),
    "ragi":         (500,    3_500),

    # Pulses
    "arhar":        (400,    2_500),
    "moong":        (300,    1_800),
    "urad":         (300,    1_800),
    "chana":        (500,    3_000),
    "lentil":       (400,    2_500),

    # Oilseeds
    "groundnut":    (600,    4_000),
    "mustard":      (400,    2_500),
    "soybean":      (600,    3_500),
    "sunflower":    (500,    2_500),

    # Vegetables
    "tomato":       (5_000,  60_000),
    "onion":        (5_000,  40_000),
    "potato":       (8_000,  40_000),
    "brinjal":      (4_000,  30_000),
    "cauliflower":  (5_000,  30_000),
    "carrot":       (8_000,  35_000),

    # Fruits
    "mango":        (2_000,  20_000),
    "banana":      (15_000,  60_000),
    "grapes":       (8_000,  30_000),
    "orange":       (5_000,  25_000),
    "pomegranate":  (5_000,  20_000),

    # Cash Crops
    "cotton":         (300,   2_500),   # lint only; model was predicting 39,980 — impossible
    "sugarcane":   (40_000, 120_000),   # bulk cane, intentionally high
    "jute":         (1_500,   4_000),
    "coffee":         (500,   3_000),
}

# Default bounds for unmapped crops (broad but physically plausible)
DEFAULT_YIELD_BOUNDS: tuple[float, float] = (100, 50_000)
