"""
Generate synthetic crop yield data for model training.

Produces realistic-looking yield data across major Indian states and crops,
with seasonal patterns, drought-year effects, and regional crop suitability.
Replace with real ICRISAT data for production use.

Output columns (matching DB schema & downstream pipeline):
    state, district, crop_name, season, year, area_ha,
    production_tonnes, yield_kg_ha, data_source

Usage:
    cd backend
    python -m scripts.download_yield_data
    python -m scripts.download_yield_data --start-year 2000 --end-year 2024
    python -m scripts.download_yield_data --seed 123 --output custom_yield.csv
"""
import argparse
import logging
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Geographic data — 12 major agricultural states, 5 districts each
# ---------------------------------------------------------------------------
STATE_DISTRICTS: dict[str, list[str]] = {
    "Maharashtra":     ["Nashik", "Pune", "Nagpur", "Aurangabad", "Solapur"],
    "Punjab":          ["Ludhiana", "Amritsar", "Patiala", "Bathinda", "Jalandhar"],
    "Madhya Pradesh":  ["Indore", "Bhopal", "Gwalior", "Jabalpur", "Rewa"],
    "Uttar Pradesh":   ["Lucknow", "Varanasi", "Agra", "Kanpur", "Meerut"],
    "Karnataka":       ["Bangalore", "Mysore", "Hubli", "Belgaum", "Gulbarga"],
    "Andhra Pradesh":  ["Guntur", "Vijayawada", "Kurnool", "Nellore", "Kadapa"],
    "Rajasthan":       ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer"],
    "Gujarat":         ["Ahmedabad", "Rajkot", "Surat", "Junagadh", "Bhavnagar"],
    "Tamil Nadu":      ["Coimbatore", "Madurai", "Thanjavur", "Salem", "Tiruchirappalli"],
    "West Bengal":     ["Bardhaman", "Hooghly", "Murshidabad", "Nadia", "Birbhum"],
    "Haryana":         ["Karnal", "Hisar", "Ambala", "Sirsa", "Rohtak"],
    "Telangana":       ["Nizamabad", "Warangal", "Karimnagar", "Khammam", "Medak"],
}

# ---------------------------------------------------------------------------
# Crop definitions — (low_yield, high_yield) in kg/ha, season, area range
# ---------------------------------------------------------------------------
CROP_CONFIGS: dict[str, dict] = {
    "rice":       {"range": (1800, 4500),  "season": "kharif",  "area": (8000, 12000)},
    "wheat":      {"range": (2200, 4500),  "season": "rabi",    "area": (8000, 12000)},
    "maize":      {"range": (1500, 3500),  "season": "kharif",  "area": (5000, 9000)},
    "cotton":     {"range": (1000, 2200),  "season": "kharif",  "area": (6000, 10000)},
    "onion":      {"range": (10000, 22000), "season": "rabi",   "area": (3000, 7000)},
    "tomato":     {"range": (15000, 30000), "season": "rabi",   "area": (2000, 5000)},
    "potato":     {"range": (12000, 22000), "season": "rabi",   "area": (4000, 8000)},
    "groundnut":  {"range": (800, 2000),   "season": "kharif",  "area": (5000, 9000)},
    "mustard":    {"range": (800, 1600),   "season": "rabi",    "area": (4000, 7000)},
    "soybean":    {"range": (800, 1800),   "season": "kharif",  "area": (5000, 9000)},
    "arhar":      {"range": (600, 1400),   "season": "kharif",  "area": (4000, 7000)},
    "moong":      {"range": (500, 1100),   "season": "kharif",  "area": (3000, 6000)},
}

# ---------------------------------------------------------------------------
# State-crop multipliers (relative advantage / disadvantage)
# ---------------------------------------------------------------------------
STATE_MULTIPLIERS: dict[tuple[str, str], float] = {
    # Punjab — breadbasket
    ("Punjab", "wheat"):           1.50,
    ("Punjab", "rice"):            1.30,
    # Haryana — similar agrozone to Punjab
    ("Haryana", "wheat"):          1.40,
    ("Haryana", "rice"):           1.20,
    # Maharashtra
    ("Maharashtra", "cotton"):     1.20,
    ("Maharashtra", "onion"):      1.15,
    ("Maharashtra", "soybean"):    1.10,
    # Uttar Pradesh
    ("Uttar Pradesh", "potato"):   1.30,
    ("Uttar Pradesh", "wheat"):    1.20,
    # Karnataka
    ("Karnataka", "rice"):         1.10,
    ("Karnataka", "groundnut"):    1.10,
    # Madhya Pradesh
    ("Madhya Pradesh", "soybean"): 1.25,
    ("Madhya Pradesh", "wheat"):   1.10,
    # Rajasthan
    ("Rajasthan", "mustard"):      1.20,
    ("Rajasthan", "groundnut"):    1.15,
    # Andhra Pradesh / Telangana — rice belt
    ("Andhra Pradesh", "rice"):    1.20,
    ("Andhra Pradesh", "cotton"):  1.10,
    ("Telangana", "rice"):         1.15,
    ("Telangana", "cotton"):       1.10,
    # Gujarat
    ("Gujarat", "cotton"):         1.25,
    ("Gujarat", "groundnut"):      1.20,
    # Tamil Nadu
    ("Tamil Nadu", "rice"):        1.15,
    # West Bengal
    ("West Bengal", "rice"):       1.25,
    ("West Bengal", "potato"):     1.15,
}

# Crops that are NOT typically grown in certain states (skip generation)
STATE_CROP_EXCLUSIONS: set[tuple[str, str]] = {
    ("Rajasthan", "rice"),
    ("Punjab", "cotton"),
    ("Tamil Nadu", "wheat"),
    ("Tamil Nadu", "mustard"),
    ("West Bengal", "mustard"),
    ("West Bengal", "cotton"),
    ("Gujarat", "potato"),
}

# ---------------------------------------------------------------------------
# Drought / excess-rain years — applied as yield multipliers
# ---------------------------------------------------------------------------
# Years with poor monsoon or climate stress; multiplier < 1 = yield drop
CLIMATE_SHOCKS: dict[int, float] = {
    1991: 0.92,  # moderate drought
    2002: 0.82,  # severe drought
    2004: 0.90,  # moderate deficit
    2009: 0.85,  # severe drought
    2012: 0.91,  # deficit monsoon
    2014: 0.88,  # drought year
    2015: 0.87,  # consecutive drought
    2018: 0.93,  # Kerala floods (localised, slight national effect)
    2023: 0.94,  # El Niño impact
}

# ---------------------------------------------------------------------------
# Trend parameters
# ---------------------------------------------------------------------------
BASE_YEAR = 1990
DEFAULT_START_YEAR = 1990
DEFAULT_END_YEAR = 2024
# Green Revolution tail-off: faster gains early, slower later
TREND_FAST = 0.008   # pre-2005 annual gain
TREND_SLOW = 0.003   # post-2005 annual gain
TREND_BREAK_YEAR = 2005

DATA_SOURCE = "ICRISAT_SYNTHETIC"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_trend(year: int) -> float:
    """Piecewise linear trend: faster pre-2005, slower post-2005."""
    if year <= TREND_BREAK_YEAR:
        return 1.0 + TREND_FAST * (year - BASE_YEAR)
    fast_portion = 1.0 + TREND_FAST * (TREND_BREAK_YEAR - BASE_YEAR)
    return fast_portion + TREND_SLOW * (year - TREND_BREAK_YEAR)


def _validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean the generated dataframe."""
    initial_len = len(df)

    # Enforce non-negative yields
    df = df[df["yield_kg_ha"] > 0].copy()

    # Clamp yields to reasonable bounds (upstream clean_yield_data expects [10, 50000])
    df = df[(df["yield_kg_ha"] >= 10) & (df["yield_kg_ha"] <= 50_000)].copy()

    # Ensure area and production are positive
    df = df[(df["area_ha"] > 0) & (df["production_tonnes"] > 0)].copy()

    dropped = initial_len - len(df)
    if dropped > 0:
        logger.warning("Validation dropped %d rows (%.2f%%)", dropped, 100 * dropped / initial_len)

    return df.reset_index(drop=True)


def _print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics for the generated dataset."""
    print("\n--- Summary Statistics ---")
    print(f"Total rows:    {len(df):,}")
    print(f"States:        {df['state'].nunique()}")
    print(f"Districts:     {df['district'].nunique()}")
    print(f"Crops:         {df['crop_name'].nunique()}")
    print(f"Year range:    {df['year'].min()} – {df['year'].max()}")
    print(f"Seasons:       {sorted(df['season'].unique())}")

    print("\nMean yield (kg/ha) by crop:")
    crop_means = (
        df.groupby("crop_name")["yield_kg_ha"]
        .mean()
        .sort_values(ascending=False)
    )
    for crop, mean_yield in crop_means.items():
        print(f"  {crop:<12s}  {mean_yield:>10,.1f}")

    print("\nMean yield (kg/ha) by state (top 5):")
    state_means = (
        df.groupby("state")["yield_kg_ha"]
        .mean()
        .sort_values(ascending=False)
        .head(5)
    )
    for state, mean_yield in state_means.items():
        print(f"  {state:<20s}  {mean_yield:>10,.1f}")

    print()


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def generate_yield_data(
    *,
    start_year: int = DEFAULT_START_YEAR,
    end_year: int = DEFAULT_END_YEAR,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate a DataFrame of synthetic crop yield records.

    Parameters
    ----------
    start_year : int
        First year of data (inclusive).
    end_year : int
        Last year of data (inclusive).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        Columns: state, district, crop_name, season, year, area_ha,
        production_tonnes, yield_kg_ha, data_source
    """
    years = list(range(start_year, end_year + 1))
    rng = np.random.default_rng(seed)
    records: list[dict] = []

    for state, districts in STATE_DISTRICTS.items():
        for district in districts:
            # Add per-district random baseline shift (±5%) for variation
            district_factor = rng.uniform(0.95, 1.05)

            for crop, cfg in CROP_CONFIGS.items():
                # Skip excluded state-crop pairs
                if (state, crop) in STATE_CROP_EXCLUSIONS:
                    continue

                low, high = cfg["range"]
                season = cfg["season"]
                area_low, area_high = cfg["area"]
                base_yield = (low + high) / 2.0
                state_mult = STATE_MULTIPLIERS.get((state, crop), 1.0)

                for year in years:
                    trend = _compute_trend(year)
                    climate_mult = CLIMATE_SHOCKS.get(year, 1.0)

                    # Gaussian noise — 8% of base yield
                    noise = rng.normal(0, 0.08 * base_yield)

                    yield_kg_ha = (
                        base_yield * state_mult * district_factor * trend * climate_mult
                        + noise
                    )
                    # Floor at half the low end
                    yield_kg_ha = max(low * 0.5, yield_kg_ha)
                    yield_kg_ha = round(yield_kg_ha, 1)

                    # Area with inter-annual variation
                    area_ha = round(rng.uniform(area_low, area_high), 0)
                    production_tonnes = round(area_ha * yield_kg_ha / 1000.0, 1)

                    records.append({
                        "state": state,
                        "district": district,
                        "crop_name": crop,
                        "season": season,
                        "year": year,
                        "area_ha": area_ha,
                        "production_tonnes": production_tonnes,
                        "yield_kg_ha": yield_kg_ha,
                        "data_source": DATA_SOURCE,
                    })

    df = pd.DataFrame(records)
    df = _validate_dataframe(df)

    # Sort for deterministic output
    df = df.sort_values(
        ["state", "district", "crop_name", "year"],
    ).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic crop yield data for model training.",
    )
    parser.add_argument(
        "--start-year", type=int, default=DEFAULT_START_YEAR,
        help=f"First year of data (default: {DEFAULT_START_YEAR})",
    )
    parser.add_argument(
        "--end-year", type=int, default=DEFAULT_END_YEAR,
        help=f"Last year of data (default: {DEFAULT_END_YEAR})",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output filename (default: yield_data_raw.csv in data/crop_yields/)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress summary statistics output",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = _parse_args()

    if args.start_year > args.end_year:
        logger.error("--start-year (%d) must be <= --end-year (%d)", args.start_year, args.end_year)
        sys.exit(1)

    output_dir = REPO_ROOT / "data" / "crop_yields"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = args.output or "yield_data_raw.csv"
    output_path = output_dir / output_filename

    logger.info(
        "Generating synthetic yield data: years=%d–%d, seed=%d",
        args.start_year, args.end_year, args.seed,
    )

    df = generate_yield_data(
        start_year=args.start_year,
        end_year=args.end_year,
        seed=args.seed,
    )

    df.to_csv(output_path, index=False)
    print(f"Generated {len(df):,} synthetic yield records -> {output_path}")
    print("NOTE: Replace with real ICRISAT data for production use.")

    if not args.quiet:
        _print_summary(df)


if __name__ == "__main__":
    main()
