"""
Soil feature engineering — block-level NPK/pH profile lookup.

DATA CONTRACT (verified against data/soil-health/nutrients/ CSVs):
- One CSV per state/district/block/cycle combination
- Filename: {STATE}_{DISTRICT}_{BLOCK} - {ID}_{cycle}.csv
- Columns: cycle, state, district, block, nutrient, high, medium, low
- Nutrient rows (always 5, always in this order):
    "Nitrogen", "Phosphorus", "Potassium", "Organic Carbon", "Potential Of Hydrogen"
- high/medium/low values are percentage strings ending in "%" — e.g. "92%", "0%", "100%"
- Example file content:
    cycle,state,district,block,nutrient,high,medium,low
    2023-24,ANDAMAN & NICOBAR,NICOBARS,CAMPBELL BAY - 6498,Nitrogen,0%,92%,8%
    2023-24,ANDAMAN & NICOBAR,NICOBARS,CAMPBELL BAY - 6498,Phosphorus,0%,65%,35%
    2023-24,ANDAMAN & NICOBAR,NICOBARS,CAMPBELL BAY - 6498,Potassium,0%,54%,46%
    2023-24,ANDAMAN & NICOBAR,NICOBARS,CAMPBELL BAY - 6498,Organic Carbon,0%,0%,100%
    2023-24,ANDAMAN & NICOBAR,NICOBARS,CAMPBELL BAY - 6498,Potential Of Hydrogen,0%,15%,85%

PURE FUNCTION CONTRACT:
- compute_soil_features() accepts a pre-loaded block DataFrame
- Zero file reads inside this function — caller responsibility
- Enables testing with synthetic data without touching the filesystem
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd


# Canonical nutrient-to-column-prefix mapping (verified against real CSV nutrient names)
_NUTRIENT_PREFIX_MAP = {
    "Nitrogen": "N",
    "Phosphorus": "P",
    "Potassium": "K",
    "Organic Carbon": "OC",
    "Potential Of Hydrogen": "pH",
}

# 15 columns: 5 nutrients × 3 levels
SOIL_NUTRIENT_COLS = [
    "N_high", "N_medium", "N_low",
    "P_high", "P_medium", "P_low",
    "K_high", "K_medium", "K_low",
    "OC_high", "OC_medium", "OC_low",
    "pH_high", "pH_medium", "pH_low",
]


def compute_soil_features(block_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract NPK/OC/pH distribution profile from a pre-loaded block CSV DataFrame.

    Args:
        block_df: DataFrame loaded from one soil health CSV for one block.
                  Expected columns: [cycle, state, district, block, nutrient, high, medium, low]
                  high/medium/low are percentage strings ending in "%" (e.g. "92%", "0%").
                  Nutrient values: "Nitrogen", "Phosphorus", "Potassium",
                                   "Organic Carbon", "Potential Of Hydrogen"

    Returns:
        pd.DataFrame with one row and columns = SOIL_NUTRIENT_COLS.
        Each value is a float in [0, 100] representing the percentage.
        Returns empty DataFrame (0 rows, SOIL_NUTRIENT_COLS columns) if block_df is
        None, empty, or missing any of the 5 required nutrient rows.
    """
    if block_df is None or block_df.empty:
        return pd.DataFrame(columns=SOIL_NUTRIENT_COLS)

    row = {}
    for nutrient_name, prefix in _NUTRIENT_PREFIX_MAP.items():
        nutrient_rows = block_df[block_df["nutrient"] == nutrient_name]
        if nutrient_rows.empty:
            # Missing nutrient — return empty rather than a partial / NaN-filled row
            return pd.DataFrame(columns=SOIL_NUTRIENT_COLS)
        r = nutrient_rows.iloc[0]
        # Strip "%" and convert to float
        row[f"{prefix}_high"] = float(str(r["high"]).rstrip("%"))
        row[f"{prefix}_medium"] = float(str(r["medium"]).rstrip("%"))
        row[f"{prefix}_low"] = float(str(r["low"]).rstrip("%"))

    return pd.DataFrame([row], columns=SOIL_NUTRIENT_COLS)
