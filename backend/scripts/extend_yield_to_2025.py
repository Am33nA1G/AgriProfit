"""
Extend real crop yield data (1997–2020) with trend-projected values for 2021–2025.

Method:
  For each (district, crop) group:
    - Fit a simple linear trend over the last 5 years of real data
    - Project forward to TARGET_YEARS with Gaussian noise (±5%)
    - Mark projected rows with data_source = "projected_linear"

The output replaces/appends to yield_data_raw.csv so the full
1997–2025 range is available for training.

Usage:
    cd backend
    python -m scripts.extend_yield_to_2025
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import logging
import numpy as np
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_PATH  = REPO_ROOT / "data" / "crop_yields" / "yield_data_raw.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "crop_yields" / "yield_data_raw.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TARGET_YEARS   = list(range(2021, 2026))   # 2021 … 2025
TREND_WINDOW   = 5                          # years of real data used to fit trend
NOISE_STD_FRAC = 0.05                       # ±5% Gaussian noise
SEED           = 42
MIN_YIELD      = 10.0
MAX_YIELD      = 50_000.0

CLIMATE_SHOCKS: dict[int, float] = {
    2023: 0.94,   # El Niño impacts
}


def _project_group(group: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    """Fit linear trend on last TREND_WINDOW years, project to TARGET_YEARS."""
    group = group.sort_values("year")
    recent = group.tail(TREND_WINDOW)

    years_arr  = recent["year"].values.astype(float)
    yields_arr = recent["yield_kg_ha"].values.astype(float)

    # Linear fit (fallback to mean if only one point)
    if len(recent) >= 2:
        slope, intercept = np.polyfit(years_arr, yields_arr, 1)
    else:
        slope, intercept = 0.0, yields_arr.mean()

    # Cap trend to ±1.5% per year of the mean (prevents wild extrapolation)
    mean_yield  = yields_arr.mean()
    max_slope   = mean_yield * 0.015
    slope       = float(np.clip(slope, -max_slope, max_slope))

    # Grab metadata from most recent real row
    last = group.iloc[-1]
    state    = last["state"]
    district = last["district"]
    crop     = last["crop_name"]
    season   = last.get("season", "unknown")
    area_ha  = float(last["area_ha"])

    rows = []
    for yr in TARGET_YEARS:
        climate = CLIMATE_SHOCKS.get(yr, 1.0)
        predicted = (slope * yr + intercept) * climate
        noise     = rng.normal(0, NOISE_STD_FRAC * mean_yield)
        yield_val = float(np.clip(predicted + noise, MIN_YIELD, MAX_YIELD))
        yield_val = round(yield_val, 1)

        # Area: small inter-annual variation around the last known area
        area = round(float(rng.uniform(area_ha * 0.95, area_ha * 1.05)), 0)
        production = round(area * yield_val / 1000.0, 1)

        rows.append({
            "state": state,
            "district": district,
            "crop_name": crop,
            "season": season,
            "year": yr,
            "area_ha": area,
            "production_tonnes": production,
            "yield_kg_ha": yield_val,
            "data_source": "projected_linear",
        })
    return rows


def main() -> None:
    if not INPUT_PATH.exists():
        logger.error("Input file not found: %s", INPUT_PATH)
        sys.exit(1)

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    logger.info("Loaded %d rows (years %d–%d)", len(df), df["year"].min(), df["year"].max())

    # Already has projected data? Remove it before re-generating
    if "data_source" in df.columns:
        real_df   = df[df["data_source"] != "projected_linear"].copy()
        dropped   = len(df) - len(real_df)
        if dropped:
            logger.info("Removed %d previously projected rows", dropped)
        df = real_df

    rng = np.random.default_rng(SEED)
    proj_records: list[dict] = []

    groups = df.groupby(["district", "crop_name"], sort=False)
    total  = len(groups)
    skipped = 0

    for (district, crop), grp in groups:
        if len(grp) < 2:
            skipped += 1
            continue
        proj_records.extend(_project_group(grp, rng))

    logger.info(
        "Projected %d rows for %d district-crop pairs (%d skipped)",
        len(proj_records), total - skipped, skipped,
    )

    proj_df = pd.DataFrame(proj_records)
    combined = pd.concat([df, proj_df], ignore_index=True)
    combined = combined.sort_values(["state", "district", "crop_name", "year"]).reset_index(drop=True)

    combined.to_csv(OUTPUT_PATH, index=False)
    logger.info("Saved %d total rows → %s", len(combined), OUTPUT_PATH)

    print(f"\nSaved {len(combined):,} rows → {OUTPUT_PATH}")
    print(f"  Real data:      {len(df):,} rows  ({df['year'].min()}–{df['year'].max()})")
    print(f"  Projected:      {len(proj_df):,} rows  (2021–2025)")
    print(f"  States:         {combined['state'].nunique()}")
    print(f"  Districts:      {combined['district'].nunique()}")
    print(f"  Crops:          {combined['crop_name'].nunique()}")
    print(f"  Full year range:{combined['year'].min()}–{combined['year'].max()}")


if __name__ == "__main__":
    main()
