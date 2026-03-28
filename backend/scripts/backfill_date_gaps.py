#!/usr/bin/env python3
"""
Backfill missing price history by fetching specific dates from data.gov.in.

Missing dates in 2026 (identified by audit):
  - Completely absent: Feb 24, Feb 27, Mar 4, Mar 7-20, Mar 23-25
  - Partially loaded:  Feb 28 (1,748), Mar 1 (1), Mar 5 (1,992), Mar 6 (7,540)

Usage:
    cd backend/
    python scripts/backfill_date_gaps.py            # dry-run (shows what will be fetched)
    python scripts/backfill_date_gaps.py --apply    # actually writes to DB
    python scripts/backfill_date_gaps.py --apply --from 2026-03-07 --to 2026-03-20
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Known gap dates in 2026 ──────────────────────────────────────────────────
# Completely missing dates
_MISSING_DATES: list[date] = [
    date(2026, 2, 24),
    date(2026, 2, 27),
    date(2026, 3, 4),
    *[date(2026, 3, d) for d in range(7, 21)],   # Mar 7–20 inclusive
    date(2026, 3, 23),
    date(2026, 3, 24),
    date(2026, 3, 25),
]

# Dates where we have data but record counts are suspiciously low — re-fetch
# to pull any records that weren't in the parquet snapshot.
_PARTIAL_DATES: list[date] = [
    date(2026, 2, 28),   # 1,748 records (normal ≈ 10K+)
    date(2026, 3, 1),    # 1 record
    date(2026, 3, 5),    # 1,992 records
    date(2026, 3, 6),    # 7,540 records
]


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def build_target_dates(
    from_date: date | None,
    to_date: date | None,
    include_partial: bool,
) -> list[date]:
    """Return the sorted list of dates to backfill."""
    if from_date and to_date:
        return sorted(_date_range(from_date, to_date))
    targets = set(_MISSING_DATES)
    if include_partial:
        targets.update(_PARTIAL_DATES)
    return sorted(targets)


def run_backfill(target_dates: list[date], apply: bool) -> None:
    from datetime import datetime

    from app.database.session import SessionLocal
    from app.integrations.data_gov_client import get_data_gov_client
    from app.integrations.seeder import DatabaseSeeder

    logger.info(
        "Backfill: %d date(s) to process (%s → %s) [%s]",
        len(target_dates),
        target_dates[0],
        target_dates[-1],
        "APPLY" if apply else "DRY-RUN",
    )

    if not apply:
        logger.info("DRY-RUN mode — pass --apply to write to DB")
        for d in target_dates:
            logger.info("  Would fetch: %s", d)
        return

    client = get_data_gov_client()
    db = SessionLocal()
    total_inserted = 0
    total_updated = 0

    try:
        seeder = DatabaseSeeder(db, client)
        seeder.preload_caches()

        for target_date in target_dates:
            dt = datetime(target_date.year, target_date.month, target_date.day)
            logger.info("Fetching %s …", target_date)

            records = client.fetch_prices_for_dates([dt])

            if not records:
                logger.warning("  → No records from API for %s (holiday/weekend?)", target_date)
                continue

            logger.info("  → %d records received, seeding…", len(records))
            seeder.seed_records(records)
            total_inserted += len(records)
            logger.info("  → Done (%s)", target_date)

    finally:
        db.close()

    logger.info(
        "Backfill complete: %d total records processed across %d date(s)",
        total_inserted,
        len(target_dates),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill missing price history from data.gov.in")
    parser.add_argument("--apply", action="store_true", help="Write results to DB (default: dry-run)")
    parser.add_argument("--from", dest="from_date", type=_parse_date, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", type=_parse_date, help="End date YYYY-MM-DD")
    parser.add_argument("--skip-partial", action="store_true", help="Skip re-fetching partial dates")
    args = parser.parse_args()

    if bool(args.from_date) != bool(args.to_date):
        parser.error("--from and --to must be used together")

    target_dates = build_target_dates(
        from_date=args.from_date,
        to_date=args.to_date,
        include_partial=not args.skip_partial,
    )

    if not target_dates:
        logger.info("No dates to backfill.")
        return 0

    run_backfill(target_dates, apply=args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
