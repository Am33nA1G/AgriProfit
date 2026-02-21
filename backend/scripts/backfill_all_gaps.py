"""
Comprehensive Backfill: Find and Fill ALL Date Gaps in Price History

Queries the database to identify ALL dates with insufficient data,
then uses the historical API resource to backfill missing records.

Reuses BackfillClient and BackfillSeeder from backfill_prices.py.

Usage:
    python scripts/backfill_all_gaps.py
    python scripts/backfill_all_gaps.py --threshold 500
    python scripts/backfill_all_gaps.py --dry-run
    python scripts/backfill_all_gaps.py --extend-to-today
"""
import sys
import os
import time
import logging
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database.session import SessionLocal

# Import reusable classes from backfill_prices.py
from scripts.backfill_prices import BackfillClient, BackfillSeeder

# Setup logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "backfill_all_gaps.log", encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Suppress httpx logging noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Key commodities to verify coverage for.
# Names use ILIKE %pattern% matching — use shortest unambiguous substring.
# data.gov.in variants: "Arhar(Tur/Red Gram)(Whole)", "Black Gram(Urd Beans)(Whole)"
KEY_COMMODITIES = [
    "Rice", "Wheat", "Tomato", "Onion", "Potato",
    "Maize", "Soyabean", "Mustard", "Groundnut",
    "Cotton", "Sugar", "Banana", "Apple",
    "Chillies", "Turmeric", "Garlic", "Ginger",
    "Arhar(Tur/Red Gram)", "Moong", "Black Gram(Urd",
]


def get_date_range(db) -> tuple[date | None, date | None]:
    """Get MIN and MAX price_date from the database.

    Uses ORDER BY + LIMIT 1 instead of MIN/MAX for efficiency
    on the idx_price_history_date (price_date DESC) index.
    """
    max_result = db.execute(text(
        "SELECT price_date FROM price_history ORDER BY price_date DESC LIMIT 1"
    )).first()
    min_result = db.execute(text(
        "SELECT price_date FROM price_history ORDER BY price_date ASC LIMIT 1"
    )).first()
    min_date = min_result[0] if min_result else None
    max_date = max_result[0] if max_result else None
    return min_date, max_date


def get_per_date_counts(db, start: date, end: date) -> dict[date, int]:
    """Get record count per date in the given range."""
    result = db.execute(text("""
        SELECT price_date, COUNT(*) as cnt
        FROM price_history
        WHERE price_date >= :start AND price_date <= :end
        GROUP BY price_date
        ORDER BY price_date
    """), {"start": start, "end": end})
    return {row[0]: row[1] for row in result}


def find_sparse_dates(
    start: date, end: date,
    existing_counts: dict[date, int],
    threshold: int = 1000,
) -> list[date]:
    """Find all dates within range that have fewer records than threshold."""
    sparse = []
    current = start
    while current <= end:
        count = existing_counts.get(current, 0)
        if count < threshold:
            sparse.append(current)
        current += timedelta(days=1)
    return sparse


def verify_coverage(db, start: date, end: date) -> dict:
    """Verify per-commodity coverage for key commodities."""
    total_days = (end - start).days + 1
    report = {}

    for commodity in KEY_COMMODITIES:
        result = db.execute(text("""
            SELECT COUNT(DISTINCT ph.price_date)
            FROM price_history ph
            JOIN commodities c ON c.id = ph.commodity_id
            WHERE c.name ILIKE :pattern
              AND ph.price_date >= :start
              AND ph.price_date <= :end
        """), {"pattern": f"%{commodity}%", "start": start, "end": end}).scalar()

        days_with_data = result or 0
        pct = (days_with_data / total_days * 100) if total_days > 0 else 0
        report[commodity] = {
            "days_with_data": days_with_data,
            "total_days": total_days,
            "coverage_pct": round(pct, 1),
        }

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Find and backfill ALL gaps in price_history"
    )
    parser.add_argument(
        "--threshold", type=int, default=1000,
        help="Dates with fewer than this many records will be backfilled (default: 1000)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only report gaps, don't fetch or insert"
    )
    parser.add_argument(
        "--extend-to-today", action="store_true",
        help="Extend the date range to today (backfill up to today)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-fetch even for dates that already have data"
    )
    parser.add_argument(
        "--start-date", default=None,
        help="Override start date YYYY-MM-DD (default: auto-detect from DB)"
    )
    parser.add_argument(
        "--end-date", default=None,
        help="Override end date YYYY-MM-DD (default: auto-detect from DB)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("COMPREHENSIVE GAP BACKFILL")
    print("=" * 70)
    print(f"Timestamp: {datetime.now()}")
    print(f"Threshold: {args.threshold} records/day")
    print(f"Dry run:   {args.dry_run}")
    print(f"Force:     {args.force}")
    print("=" * 70)

    db = SessionLocal()
    client = BackfillClient()

    try:
        # 1. Determine date range
        logger.info("Step 1: Determining date range...")
        db_min, db_max = get_date_range(db)

        if not db_min or not db_max:
            logger.error("No data in price_history table! Cannot determine range.")
            return 1

        start = date.fromisoformat(args.start_date) if args.start_date else db_min
        end = date.fromisoformat(args.end_date) if args.end_date else db_max

        if args.extend_to_today:
            end = max(end, date.today())

        total_days = (end - start).days + 1
        logger.info(f"  Database range: {db_min} to {db_max}")
        logger.info(f"  Backfill range: {start} to {end} ({total_days} days)")

        # 2. Get existing per-date record counts
        logger.info("\nStep 2: Analyzing existing data coverage...")
        existing_counts = get_per_date_counts(db, start, end)
        dates_with_data = len(existing_counts)
        dates_without_data = total_days - dates_with_data

        logger.info(f"  Dates with data:    {dates_with_data}/{total_days}")
        logger.info(f"  Dates without data: {dates_without_data}")

        # 3. Find sparse dates
        logger.info(f"\nStep 3: Finding dates with < {args.threshold} records...")
        if args.force:
            sparse_dates = []
            current = start
            while current <= end:
                sparse_dates.append(current)
                current += timedelta(days=1)
        else:
            sparse_dates = find_sparse_dates(start, end, existing_counts, args.threshold)

        if not sparse_dates:
            logger.info("  No sparse dates found! All dates have sufficient data.")
            print("\n" + "=" * 70)
            print("NO GAPS FOUND - Database is complete!")
            print("=" * 70)
        else:
            logger.info(f"  Found {len(sparse_dates)} dates needing backfill")

            # Show sample of dates
            zero_dates = [d for d in sparse_dates if existing_counts.get(d, 0) == 0]
            sparse_only = [d for d in sparse_dates if 0 < existing_counts.get(d, 0) < args.threshold]
            logger.info(f"    Dates with ZERO data:  {len(zero_dates)}")
            logger.info(f"    Dates with sparse data: {len(sparse_only)}")

            if zero_dates[:5]:
                logger.info(f"    Sample zero dates: {', '.join(str(d) for d in zero_dates[:5])}")
            if sparse_only[:5]:
                logger.info(f"    Sample sparse dates: {', '.join(f'{d} ({existing_counts[d]})' for d in sparse_only[:5])}")

        if args.dry_run:
            logger.info("\n[DRY RUN] Skipping fetch and insert.")
        elif sparse_dates:
            # 4. Backfill sparse dates
            logger.info(f"\nStep 4: Backfilling {len(sparse_dates)} dates...")
            seeder = BackfillSeeder(db)
            seeder.load_caches()

            overall_start = time.time()
            total_fetched = 0
            total_inserted = 0
            errors = []

            for idx, target_date in enumerate(sparse_dates, 1):
                date_str = target_date.strftime("%d/%m/%Y")
                existing = existing_counts.get(target_date, 0)
                logger.info(
                    f"[{idx}/{len(sparse_dates)}] {target_date} "
                    f"(existing: {existing:,}) - Fetching..."
                )

                try:
                    records = client.fetch_all_for_date(date_str)
                    total_fetched += len(records)

                    if not records:
                        logger.info(f"  No records available from API for {target_date}")
                        continue

                    logger.info(f"  Fetched {len(records):,} records from API")
                    created = seeder.seed_day(records, target_date)
                    total_inserted += created
                    logger.info(
                        f"  Inserted/updated {created:,} records "
                        f"(running total: {total_inserted:,})"
                    )

                except Exception as e:
                    error_msg = f"{target_date}: {type(e).__name__}: {str(e)[:100]}"
                    errors.append(error_msg)
                    logger.error(f"  ERROR: {error_msg}")

                # Rate limiting between days
                time.sleep(5.0)

                # Progress report every 10 days
                if idx % 10 == 0:
                    elapsed = time.time() - overall_start
                    rate = idx / (elapsed / 60) if elapsed > 0 else 0
                    remaining = len(sparse_dates) - idx
                    eta = remaining / rate if rate > 0 else 0
                    logger.info(
                        f"  --- PROGRESS: {idx}/{len(sparse_dates)} dates | "
                        f"{total_fetched:,} fetched | {total_inserted:,} inserted | "
                        f"Rate: {rate:.1f} days/min | ETA: {eta:.0f} min ---"
                    )

            elapsed = time.time() - overall_start
            print(f"\n{'=' * 70}")
            print("BACKFILL RESULTS")
            print(f"{'=' * 70}")
            print(f"Duration:          {elapsed / 60:.1f} minutes")
            print(f"Dates processed:   {len(sparse_dates)}")
            print(f"API records:       {total_fetched:,}")
            print(f"Records inserted:  {total_inserted:,}")
            print(f"API requests:      {client.request_count}")
            print(f"Data transfer:     {client.total_bytes / 1024 / 1024:.1f} MB")
            print(f"New commodities:   {seeder.stats['new_commodities']}")
            print(f"New mandis:        {seeder.stats['new_mandis']}")

            if errors:
                print(f"\nErrors ({len(errors)}):")
                for err in errors[:20]:
                    print(f"  {err}")

        # 5. Verify coverage
        logger.info(f"\nStep 5: Verifying per-commodity coverage...")
        coverage = verify_coverage(db, start, end)

        print(f"\n{'=' * 70}")
        print("PER-COMMODITY COVERAGE REPORT")
        print(f"{'=' * 70}")
        print(f"{'Commodity':<30} {'Days':>6} {'Total':>6} {'Coverage':>10}")
        print("-" * 55)

        good_count = 0
        warning_count = 0
        for commodity, stats in sorted(coverage.items(), key=lambda x: x[1]["coverage_pct"], reverse=True):
            pct = stats["coverage_pct"]
            status = "OK" if pct >= 80 else "LOW" if pct >= 50 else "CRITICAL"
            if pct >= 80:
                good_count += 1
            else:
                warning_count += 1
            print(
                f"  {commodity:<28} {stats['days_with_data']:>6} "
                f"{stats['total_days']:>6} {pct:>8.1f}%  [{status}]"
            )

        print(f"\n  Summary: {good_count} commodities OK, {warning_count} need attention")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user.")
        return 1

    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return 1

    finally:
        client.close()
        db.close()


if __name__ == "__main__":
    sys.exit(main())
