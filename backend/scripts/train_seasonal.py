"""
Seasonal price calendar: offline aggregation pipeline.

Reads the 25M-row price parquet, applies per-commodity price_bounds caps,
computes monthly median+IQR per (commodity, state, month), and upserts
all results into the seasonal_price_stats PostgreSQL table.

This script is designed to be run once after Phase 1 completes (price_bounds
already seeded). It is idempotent — re-runs upsert via ON CONFLICT.

Usage:
    python backend/scripts/train_seasonal.py

Expected runtime: 3-8 minutes (25M row parquet load + groupby + upsert).
"""
import sys
import os
from pathlib import Path

# Windows UTF-8 console fix (project standard from MEMORY.md)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
from sqlalchemy import create_engine

# Add backend/ to sys.path so app imports work when run as a script
_BACKEND_DIR = Path(__file__).parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Load env before any app imports
from dotenv import load_dotenv
load_dotenv(_BACKEND_DIR / ".env")

from app.database.session import SessionLocal
from app.ml.seasonal.aggregator import (
    load_and_prepare,
    compute_seasonal_stats,
    upsert_seasonal_stats,
)

# Path to price parquet — repo root / agmarknet_daily_10yr.parquet
_PARQUET_PATH = Path(__file__).parent.parent.parent / "agmarknet_daily_10yr.parquet"


def main() -> None:
    """
    Full seasonal aggregation pipeline.

    Steps:
    1. Load parquet + apply price bounds caps
    2. Compute seasonal stats (pure function)
    3. Upsert into seasonal_price_stats
    4. Spot-check validation
    """
    print("=== Seasonal Price Calendar: Aggregation Pipeline ===")
    print(f"Parquet path: {_PARQUET_PATH}")

    # Create SQLAlchemy engine for reads
    db = SessionLocal()
    engine = db.get_bind()

    try:
        # Step 1: Load parquet + apply price bounds caps
        print("\n[1/4] Loading parquet + applying price bounds caps...")
        df = load_and_prepare(_PARQUET_PATH, engine)
        print(f"  Loaded {len(df):,} rows")
        print(f"  Unique commodities: {df['commodity'].nunique()}")
        print(f"  Unique states: {df['state'].nunique()}")

        # Step 2: Compute seasonal stats (pure function)
        print("\n[2/4] Computing seasonal stats (this may take 3-8 minutes)...")
        stats_df = compute_seasonal_stats(df)
        print(f"  Output rows: {len(stats_df):,}")
        print(f"  Unique (commodity, state) pairs: "
              f"{stats_df.groupby(['commodity_name', 'state_name']).ngroups:,}")

        # Step 3: Upsert into seasonal_price_stats
        print("\n[3/4] Upserting into seasonal_price_stats...")
        rows_written = upsert_seasonal_stats(stats_df, engine)
        print(f"  Rows written: {rows_written:,}")

        # Step 4: Spot-check validation
        print("\n[4/4] Spot-check validation...")

        # Onion in Maharashtra — expect is_best=True for months 10 or 11
        onion_mh = pd.read_sql(
            "SELECT month, median_price, is_best, is_worst, years_of_data "
            "FROM seasonal_price_stats "
            "WHERE commodity_name = 'Onion' AND state_name = 'Maharashtra' "
            "ORDER BY month",
            con=engine,
        )
        print("\n--- Spot-check: Onion / Maharashtra ---")
        if len(onion_mh) > 0:
            print(onion_mh.to_string(index=False))
        else:
            print("  No data found for Onion/Maharashtra")

        # Tomato in West Bengal — expect is_best=True for month 7
        tomato_wb = pd.read_sql(
            "SELECT month, median_price, is_best, is_worst, years_of_data "
            "FROM seasonal_price_stats "
            "WHERE commodity_name = 'Tomato' AND state_name = 'West Bengal' "
            "ORDER BY month",
            con=engine,
        )
        print("\n--- Spot-check: Tomato / West Bengal ---")
        if len(tomato_wb) > 0:
            print(tomato_wb.to_string(index=False))
        else:
            print("  No data found for Tomato/West Bengal")

        # Final summary
        total = pd.read_sql(
            "SELECT COUNT(*) as cnt FROM seasonal_price_stats",
            con=engine,
        )
        print(f"\n=== train_seasonal.py complete ===")
        print(f"Rows in seasonal_price_stats: {total['cnt'].iloc[0]:,}")
        print("Run spot-check to verify: onion should peak Oct-Nov in Maharashtra, "
              "tomato in Jul in West Bengal.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
