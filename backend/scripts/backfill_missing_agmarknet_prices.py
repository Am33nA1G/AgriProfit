#!/usr/bin/env python3
"""
Backfill missing commodity price history from the Agmarknet parquet snapshot.

This script targets the commodity gaps reported by audit_database_consistency.py.
It filters the existing agmarknet_daily_10yr.parquet down to only the missing
commodities, normalizes known source-name mismatches, writes a compact parquet,
and can optionally import that subset into PostgreSQL via the existing ETL.

Usage:
    python scripts/backfill_missing_agmarknet_prices.py
    python scripts/backfill_missing_agmarknet_prices.py --apply --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.etl_parquet_to_postgres import ParquetToPostgresETL


DEFAULT_REPORT_PATH = PROJECT_ROOT / "database_gaps_report.json"
DEFAULT_SOURCE_PARQUET = REPO_ROOT / "agmarknet_daily_10yr.parquet"
DEFAULT_OUTPUT_PARQUET = PROJECT_ROOT / "tmp_missing_agmarknet_backfill.parquet"

# Source parquet names -> existing DB commodity names.
SOURCE_TO_DB_NAME = {
    "Black Gram (Urad Beans)(Whole)": "Black Gram (Urd Beans)(Whole)",
    "Pigeon Pea (Arhar Fali)": "Pegeon Pea (Arhar Fali)",
}

REQUIRED_COLUMNS = [
    "date",
    "commodity",
    "commodity_id",
    "state",
    "state_id",
    "district",
    "district_id",
    "price_min",
    "price_max",
    "price_modal",
]


def load_missing_commodities(report_path: Path) -> list[str]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return [item["name"] for item in report.get("commodity_gaps", [])]


def build_subset(
    source_parquet: Path,
    output_parquet: Path,
    target_names: list[str],
) -> tuple[int, int]:
    df = pd.read_parquet(source_parquet, columns=REQUIRED_COLUMNS)
    df["commodity"] = df["commodity"].replace(SOURCE_TO_DB_NAME)

    subset = df[df["commodity"].isin(set(target_names))].copy()
    subset.to_parquet(output_parquet, index=False)
    return len(df), len(subset)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill missing commodity prices from the Agmarknet parquet snapshot."
    )
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--source-parquet", default=str(DEFAULT_SOURCE_PARQUET))
    parser.add_argument("--output-parquet", default=str(DEFAULT_OUTPUT_PARQUET))
    parser.add_argument("--apply", action="store_true", help="Import the filtered parquet into PostgreSQL")
    parser.add_argument("--force", action="store_true", help="Skip ETL confirmation prompt")
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    report_path = Path(args.report_path)
    source_parquet = Path(args.source_parquet)
    output_parquet = Path(args.output_parquet)

    if not report_path.exists():
        raise FileNotFoundError(f"Gap report not found: {report_path}")
    if not source_parquet.exists():
        raise FileNotFoundError(f"Source parquet not found: {source_parquet}")

    target_names = load_missing_commodities(report_path)
    if not target_names:
        print("No commodity gaps found in the report.")
        return 0

    print(f"Loading commodity gaps from: {report_path}")
    print(f"Missing commodities to backfill: {len(target_names)}")
    print(f"Filtering source parquet: {source_parquet}")

    total_rows, subset_rows = build_subset(source_parquet, output_parquet, target_names)

    print(f"Source rows scanned: {total_rows:,}")
    print(f"Backfill rows written: {subset_rows:,}")
    print(f"Subset parquet written to: {output_parquet}")

    if not args.apply:
        print("Dry mode only. Re-run with --apply to import into PostgreSQL.")
        return 0

    print("Starting ETL import for the filtered parquet...")
    etl = ParquetToPostgresETL(
        parquet_path=str(output_parquet),
        batch_size=args.batch_size,
        dry_run=False,
        skip_validation=args.skip_validation,
        force=args.force,
    )
    etl.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
