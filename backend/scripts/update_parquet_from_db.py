#!/usr/bin/env python
"""
update_parquet_from_db.py — Incrementally extend the training parquet with
fresh rows from the DB that are newer than the parquet's current max date.

Usage:
    python backend/scripts/update_parquet_from_db.py

What it does:
    1. Reads max(date) from the existing parquet
    2. Queries price_history WHERE price_date > max_date
    3. Appends new rows (using the same column schema) and overwrites the parquet
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sqlalchemy import create_engine, text

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PARQUET_PATH = REPO_ROOT / "agmarknet_daily_10yr.parquet"

_NEW_ROWS_QUERY = text("""
    SELECT
        ph.price_date           AS date,
        c.name                  AS commodity,
        0                       AS commodity_id,
        m.state                 AS state,
        0                       AS state_id,
        m.district              AS district,
        0                       AS district_id,
        COALESCE(ph.min_price, ph.modal_price)   AS price_min,
        COALESCE(ph.max_price, ph.modal_price)   AS price_max,
        ph.modal_price          AS price_modal,
        0                       AS category_id,
        ''                      AS entity_id
    FROM price_history ph
    JOIN mandis      m ON ph.mandi_id = m.id
    JOIN commodities c ON ph.commodity_id = c.id
    WHERE ph.price_date > :since
      AND ph.modal_price > 0
    ORDER BY ph.price_date
""")


def main() -> None:
    print(f"Parquet path: {PARQUET_PATH}")

    print("Reading existing parquet …")
    existing = pd.read_parquet(PARQUET_PATH)
    existing["date"] = pd.to_datetime(existing["date"])
    max_date = existing["date"].max()
    print(f"  Existing rows : {len(existing):,}")
    print(f"  Max date      : {max_date.date()}")

    engine = create_engine(str(settings.database_url), echo=False)
    print(f"\nQuerying DB for rows after {max_date.date()} …")

    with engine.connect() as conn:
        new_df = pd.read_sql(
            _NEW_ROWS_QUERY,
            conn,
            params={"since": max_date.date()},
        )

    if new_df.empty:
        print("No new rows — parquet is already up to date.")
        return

    new_df["date"] = pd.to_datetime(new_df["date"])
    print(f"  New rows      : {len(new_df):,}")
    print(f"  New max date  : {new_df['date'].max().date()}")
    print(f"  New commodities covered: {new_df['commodity'].nunique()}")

    # Align dtypes to match existing parquet schema
    for col in ["price_min", "price_max", "price_modal"]:
        new_df[col] = new_df[col].astype(float)
    new_df["commodity_id"] = new_df["commodity_id"].astype(int)
    new_df["state_id"] = new_df["state_id"].astype(int)
    new_df["district_id"] = new_df["district_id"].astype(int)
    new_df["category_id"] = new_df["category_id"].astype(int)
    new_df["entity_id"] = new_df["entity_id"].astype(str)

    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["date", "commodity", "district"],
        keep="last",
    )
    combined = combined.sort_values(["commodity", "district", "date"]).reset_index(drop=True)

    print(f"\nSaving updated parquet …")
    print(f"  Total rows    : {len(combined):,}  (+{len(combined) - len(existing):,})")
    print(f"  Final max date: {combined['date'].max().date()}")

    combined.to_parquet(PARQUET_PATH, index=False)
    print("Done.")


if __name__ == "__main__":
    main()
