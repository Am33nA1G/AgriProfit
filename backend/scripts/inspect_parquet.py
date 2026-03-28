#!/usr/bin/env python3
"""
Inspect the Parquet file to understand its schema, data quality, and
column mapping requirements before running the ETL migration.

Usage:
    python scripts/inspect_parquet.py [--parquet-path PATH]
"""

import argparse
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np


DEFAULT_PARQUET = str(Path(__file__).resolve().parents[2] / "agmarknet_daily_10yr.parquet")


def inspect(parquet_path: str) -> None:
    path = Path(parquet_path)
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    file_size_mb = path.stat().st_size / (1024 * 1024)
    print("=" * 80)
    print("PARQUET FILE INSPECTION")
    print("=" * 80)
    print(f"\nFile: {path}")
    print(f"Size: {file_size_mb:.2f} MB")

    # ------------------------------------------------------------------
    # Read file
    # ------------------------------------------------------------------
    print("\nReading Parquet file ...")
    df = pd.read_parquet(parquet_path, engine="pyarrow")

    print(f"Total rows:    {len(df):,}")
    print(f"Total columns: {len(df.columns)}")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    print("\n--- Column Names and Types ---")
    for col in df.columns:
        print(f"  {col:20s}  {str(df[col].dtype):15s}")

    # ------------------------------------------------------------------
    # Sample data
    # ------------------------------------------------------------------
    print("\n--- First 5 Rows ---")
    print(df.head().to_string(index=False))

    # ------------------------------------------------------------------
    # Descriptive statistics
    # ------------------------------------------------------------------
    print("\n--- Numeric Summary ---")
    print(df.describe().to_string())

    # ------------------------------------------------------------------
    # Null / NaN counts
    # ------------------------------------------------------------------
    print("\n--- Null / NaN Counts ---")
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        pct = null_count / len(df) * 100
        flag = "  <<<" if null_count > 0 else ""
        print(f"  {col:20s}  {null_count:>12,}  ({pct:5.2f}%){flag}")

    # ------------------------------------------------------------------
    # Unique value counts
    # ------------------------------------------------------------------
    print("\n--- Unique Values ---")
    for col in df.columns:
        nunique = df[col].nunique()
        print(f"  {col:20s}  {nunique:>10,}")

    # ------------------------------------------------------------------
    # Potential issues
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("POTENTIAL ISSUES")
    print("=" * 80)

    # Price columns
    for price_col in ("price_modal", "price_min", "price_max"):
        if price_col not in df.columns:
            continue
        negatives = int((df[price_col] < 0).sum())
        zeros = int((df[price_col] == 0).sum())
        nans = int(df[price_col].isna().sum())
        print(f"  {price_col}:  negatives={negatives:,}  zeros={zeros:,}  NaN={nans:,}")

    # Date range
    if "date" in df.columns:
        print(f"\n  Date range: {df['date'].min()} to {df['date'].max()}")

    # Commodity + district uniqueness
    if {"commodity", "state", "district"}.issubset(df.columns):
        unique_commodities = df["commodity"].nunique()
        unique_districts = df["district"].nunique()
        unique_states = df["state"].nunique()
        print(f"\n  Unique commodities: {unique_commodities:,}")
        print(f"  Unique states:      {unique_states:,}")
        print(f"  Unique districts:   {unique_districts:,}")

        # Check for same district name in different states
        if "district" in df.columns and "state" in df.columns:
            district_states = df.groupby("district")["state"].nunique()
            ambiguous = district_states[district_states > 1]
            if len(ambiguous) > 0:
                print(f"\n  WARNING: {len(ambiguous)} district names appear in multiple states:")
                for dist, cnt in ambiguous.head(20).items():
                    states_list = df[df["district"] == dist]["state"].unique()
                    print(f"    {dist} -> {list(states_list)}")

    # ------------------------------------------------------------------
    # Column mapping suggestion
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("SUGGESTED COLUMN MAPPING  (Parquet -> PriceHistory)")
    print("=" * 80)
    print("""
  Parquet Column     ->  PriceHistory Field
  ----------------       ------------------
  date               ->  price_date
  commodity          ->  (lookup) -> commodity_id
  state + district   ->  (lookup/create Mandi) -> mandi_id
  district           ->  mandi_name
  price_modal        ->  modal_price
  price_min          ->  min_price
  price_max          ->  max_price
    """)

    print("=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Parquet file for ETL")
    parser.add_argument(
        "--parquet-path",
        default=DEFAULT_PARQUET,
        help=f"Path to Parquet file (default: {DEFAULT_PARQUET})",
    )
    args = parser.parse_args()
    inspect(args.parquet_path)


if __name__ == "__main__":
    main()
