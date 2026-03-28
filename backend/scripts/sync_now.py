#!/usr/bin/env python3
"""
Manual Price Sync

Triggers an immediate price data sync from data.gov.in to PostgreSQL.
Useful for testing or one-off updates outside the scheduled interval.

Usage:
    python scripts/sync_now.py [--limit N]
"""

import argparse
import logging
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually sync price data")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of API records to fetch (default: all)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    logger = logging.getLogger("sync_now")

    from app.integrations.data_sync import get_sync_service

    service = get_sync_service()

    if service.is_running:
        logger.error("A sync is already in progress. Try again later.")
        sys.exit(1)

    logger.info("Starting manual price sync...")
    result = service.sync(limit=args.limit)

    print()
    print("=" * 60)
    print("  SYNC RESULT")
    print("=" * 60)
    print(f"  Status          : {result.status.value}")
    print(f"  Started         : {result.started_at}")
    print(f"  Finished        : {result.finished_at}")
    print(f"  Duration        : {result.duration_seconds:.1f}s")
    print(f"  Records fetched : {result.records_fetched:,}")
    if result.error:
        print(f"  Error           : {result.error}")
    print("=" * 60)

    sys.exit(0 if result.status.value == "success" else 1)


if __name__ == "__main__":
    main()
