"""
Clean raw yield data: filter outliers, forward-fill gaps, compute rolling averages.

Usage:
    cd backend
    python -m scripts.clean_yield_data
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    input_path = REPO_ROOT / "data" / "crop_yields" / "yield_data_raw.csv"
    output_dir = REPO_ROOT / "data" / "crop_yields"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "yield_data_clean.parquet"

    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} rows from {input_path.name}")

    # Drop clearly impossible values first (negative, zero, or above human-record yields)
    before = len(df)
    df = df[(df["yield_kg_ha"] >= 10) & (df["yield_kg_ha"] <= 100_000)].copy()
    print(f"Dropped {before - len(df)} globally impossible rows (< 10 or > 100000 kg/ha)")

    # Per-crop outlier removal using a two-stage approach:
    # Stage 1 — identify the "core" distribution: values <= 5 * crop median.
    #   This isolates the realistic cluster even in bimodal distributions where
    #   data.gov.in mixes correct yields (~800 kg/ha arhar) with calculation
    #   errors (~30000 kg/ha arhar) caused by inconsistent area/production units.
    # Stage 2 — compute Tukey fence (Q75 + 3*IQR) on the core, then drop all
    #   rows above that fence (including the second cluster and the 50000 sentinel).
    before = len(df)
    rows_to_keep = []
    for crop, grp in df.groupby("crop_name"):
        med = grp["yield_kg_ha"].median()
        # Stage 1: core data using 5× median as initial upper bound
        core = grp["yield_kg_ha"][grp["yield_kg_ha"] <= med * 5]
        if len(core) < 10:
            rows_to_keep.append(grp)
            continue
        q25 = core.quantile(0.25)
        q75 = core.quantile(0.75)
        iqr = q75 - q25
        upper = q75 + 3.0 * iqr
        lower = max(10, q25 - 3.0 * iqr)
        valid = grp[(grp["yield_kg_ha"] >= lower) & (grp["yield_kg_ha"] <= upper)]
        rows_to_keep.append(valid)
        n_dropped = len(grp) - len(valid)
        if n_dropped > 0:
            print(f"  [{crop}] capped at {upper:.0f} kg/ha (core fence) — dropped {n_dropped} outlier rows")
    df = pd.concat(rows_to_keep, ignore_index=True)
    print(f"Per-crop outlier removal: dropped {before - len(df)} rows total — {len(df)} remain")

    # Sort for groupby operations
    df = df.sort_values(["district", "crop_name", "year"]).reset_index(drop=True)

    # Forward-fill within (district, crop_name) groups, limit 2 years
    df["yield_kg_ha"] = (
        df.groupby(["district", "crop_name"])["yield_kg_ha"]
        .transform(lambda s: s.ffill(limit=2))
    )

    # 5-year rolling average per (district, crop_name)
    df["yield_5yr_avg"] = (
        df.groupby(["district", "crop_name"])["yield_kg_ha"]
        .transform(lambda s: s.rolling(window=5, min_periods=1).mean())
    )

    result = df[["state", "district", "crop_name", "year", "yield_kg_ha", "yield_5yr_avg"]].copy()
    result.to_parquet(output_path, engine="pyarrow", index=False)

    print(f"\nSaved: {output_path}")
    print(f"Shape: {result.shape}")
    print(result.describe().to_string())


if __name__ == "__main__":
    main()
