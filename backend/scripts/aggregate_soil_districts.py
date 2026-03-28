"""
Aggregate soil nutrient data from block-level to district-level.

Reads nutrients_all.parquet, filters to most recent cycle per (state, district),
computes representative N/P/K/pH values, and saves one row per district.

Usage:
    cd backend
    python -m scripts.aggregate_soil_districts
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Representative values (midpoint estimates) for weighted average
NUTRIENT_CONFIG = {
    "Nitrogen":              {"high": 140.0, "med": 85.0, "low": 40.0, "col": "N_kg_ha"},
    "Phosphorus":            {"high": 25.0,  "med": 15.0, "low": 8.0,  "col": "P_kg_ha"},
    "Potassium":             {"high": 200.0, "med": 130.0, "low": 80.0, "col": "K_kg_ha"},
    "Potential Of Hydrogen": {"high": 7.8,   "med": 6.8,  "low": 5.8,  "col": "pH"},
}

# Nutrients we care about (skip Organic Carbon)
TARGET_NUTRIENTS = set(NUTRIENT_CONFIG.keys())


def main():
    input_path = REPO_ROOT / "data" / "soil-health" / "nutrients_all.parquet"
    output_dir = REPO_ROOT / "data" / "soil-health"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "district_soil_aggregated.parquet"

    df = pd.read_parquet(input_path, engine="pyarrow")
    print(f"Loaded {len(df)} rows from {input_path.name}")

    # Filter to target nutrients only
    df = df[df["nutrient"].isin(TARGET_NUTRIENTS)].copy()

    # Keep most recent cycle per (state, district)
    cycle_rank = (
        df.groupby(["state", "district"])["cycle"]
        .transform("max")
    )
    df = df[df["cycle"] == cycle_rank].copy()

    # Aggregate blocks to district level: mean of high/medium/low percentages
    district_agg = (
        df.groupby(["state", "district", "nutrient"])[["high", "medium", "low"]]
        .mean()
        .reset_index()
    )

    # Compute representative value per nutrient
    rows = []
    for (state, district), grp in district_agg.groupby(["state", "district"]):
        row = {"state": state, "district": district}
        for _, r in grp.iterrows():
            nutrient = r["nutrient"]
            if nutrient not in NUTRIENT_CONFIG:
                continue
            cfg = NUTRIENT_CONFIG[nutrient]
            repr_val = (r["high"] * cfg["high"] + r["medium"] * cfg["med"] + r["low"] * cfg["low"]) / 100.0
            row[cfg["col"]] = round(repr_val, 2)
        rows.append(row)

    result = pd.DataFrame(rows)
    result.to_parquet(output_path, engine="pyarrow", index=False)
    print(f"Aggregated {len(result)} districts. Output: {output_path}")


if __name__ == "__main__":
    main()
