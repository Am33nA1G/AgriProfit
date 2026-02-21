#!/usr/bin/env python3
"""
Data reconciliation CLI.

Detects gaps in price_history and fills them from the data.gov.in
historical Agmarknet resource.  Safe to run alongside the regular
6-hourly sync — uses INSERT … ON CONFLICT to avoid duplicates.

Usage:
    python scripts/reconcile_data.py --last-7-days --dry-run
    python scripts/reconcile_data.py --last-30-days
    python scripts/reconcile_data.py --start 2026-01-01 --end 2026-02-15
    python scripts/reconcile_data.py --last-7-days --sparse-threshold 1000
"""
import argparse
import logging
import sys
import os
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows console encoding fix
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Backend root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database.session import SessionLocal
from app.integrations.reconciler import DataReconciler
from app.integrations.gap_detector import GapDetector

# Logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "reconciliation.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("reconcile_data")

# Suppress noisy HTTP loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def cmd_reconcile(args):
    """Run gap detection + backfill."""
    start_date, end_date = _resolve_dates(args)
    if not start_date:
        return 1

    print("=" * 66)
    print("  AGRIPROFIT DATA RECONCILIATION")
    print("=" * 66)
    print(f"  Period        : {start_date}  →  {end_date}")
    print(f"  Sparse thresh : {args.sparse_threshold} records/day")
    print(f"  Mode          : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 66)

    db = SessionLocal()
    try:
        reconciler = DataReconciler(db)
        stats = reconciler.reconcile(
            start_date=start_date,
            end_date=end_date,
            dry_run=args.dry_run,
            sparse_threshold=args.sparse_threshold,
        )

        print()
        print("=" * 66)
        print("  RESULTS")
        print("-" * 66)
        print(f"  Gaps detected       : {stats.gaps_detected}")
        print(f"  Gaps attempted      : {stats.gaps_attempted}")
        print(f"  Gaps filled         : {stats.gaps_filled}")
        print(f"  Records fetched     : {stats.records_fetched:,}")
        print(f"  Records upserted    : {stats.records_upserted:,}")
        print(f"  Records skipped     : {stats.records_skipped:,}")
        print(f"  New commodities     : {stats.new_commodities}")
        print(f"  New mandis          : {stats.new_mandis}")
        print(f"  Errors              : {len(stats.errors)}")

        if stats.errors:
            print()
            print("  ERRORS:")
            for err in stats.errors[:10]:
                print(f"    • {err}")
            if len(stats.errors) > 10:
                print(f"    ... and {len(stats.errors) - 10} more")

        print("=" * 66)
        return 0 if not stats.errors else 1

    finally:
        db.close()


def cmd_report(args):
    """Print gap report without filling anything."""
    start_date, end_date = _resolve_dates(args)
    if not start_date:
        return 1

    db = SessionLocal()
    try:
        detector = GapDetector(db)
        summary = detector.detect_gaps(
            start_date, end_date, args.sparse_threshold
        )

        print("=" * 66)
        print("  DATA GAP REPORT")
        print("=" * 66)
        print(f"  Period              : {start_date}  →  {end_date}")
        print(f"  Total days          : {summary.total_days}")
        print(f"  Complete            : {summary.days_complete}")
        print(f"  Sparse (< {args.sparse_threshold:,})   : {summary.days_sparse}")
        print(f"  Missing (0 records) : {summary.days_missing}")
        print(f"  Weekend / holiday   : {summary.days_weekend_holiday}")
        print("-" * 66)

        if summary.gaps:
            print("  GAPS:")
            for gap in summary.gaps:
                marker = "!!" if gap.severity == "high" else " ·"
                print(f"  {marker} {gap.gap_date}  [{gap.severity:6s}]  {gap.details}")
        else:
            print("  No gaps detected — data looks complete!")

        print("=" * 66)

        # Commodity gaps
        if args.commodity_check:
            cgaps = detector.detect_commodity_gaps(start_date, end_date)
            if cgaps:
                print()
                print("  COMMODITY-LEVEL GAPS:")
                for cg in cgaps:
                    print(f"    {cg.commodity_name}: {cg.details}")
                print()

        return 0
    finally:
        db.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _resolve_dates(args):
    """Determine start/end dates from CLI arguments."""
    if args.last_7_days:
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
    elif args.last_30_days:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    elif args.last_60_days:
        end_date = date.today()
        start_date = end_date - timedelta(days=60)
    elif args.start and args.end:
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD.")
            return None, None
    else:
        logger.error(
            "Specify a date range: --last-7-days, --last-30-days, "
            "--last-60-days, or --start/--end"
        )
        return None, None

    return start_date, end_date


def main():
    parser = argparse.ArgumentParser(
        description="Detect and fill price data gaps"
    )
    sub = parser.add_subparsers(dest="command")

    # Common date arguments
    date_args = argparse.ArgumentParser(add_help=False)
    date_args.add_argument("--start", help="Start date (YYYY-MM-DD)")
    date_args.add_argument("--end", help="End date (YYYY-MM-DD)")
    date_args.add_argument("--last-7-days", action="store_true")
    date_args.add_argument("--last-30-days", action="store_true")
    date_args.add_argument("--last-60-days", action="store_true")
    date_args.add_argument(
        "--sparse-threshold",
        type=int,
        default=GapDetector.DEFAULT_SPARSE_THRESHOLD,
        help=f"Records/day below which a day is 'sparse' (default: {GapDetector.DEFAULT_SPARSE_THRESHOLD})",
    )

    # Sub-commands
    p_reconcile = sub.add_parser(
        "fill", parents=[date_args],
        help="Detect gaps and fill from fallback source",
    )
    p_reconcile.add_argument(
        "--dry-run", action="store_true",
        help="Detect gaps without inserting data",
    )

    p_report = sub.add_parser(
        "report", parents=[date_args],
        help="Print gap report (read-only)",
    )
    p_report.add_argument(
        "--commodity-check", action="store_true",
        help="Also check commodity-level gaps",
    )

    args = parser.parse_args()

    if args.command == "fill":
        return cmd_reconcile(args)
    elif args.command == "report":
        return cmd_report(args)
    else:
        # Default: if no sub-command, treat as reconcile with common args
        # Re-parse with reconcile defaults
        parser2 = argparse.ArgumentParser(
            description="Detect and fill price data gaps"
        )
        parser2.add_argument("--start", help="Start date (YYYY-MM-DD)")
        parser2.add_argument("--end", help="End date (YYYY-MM-DD)")
        parser2.add_argument("--last-7-days", action="store_true")
        parser2.add_argument("--last-30-days", action="store_true")
        parser2.add_argument("--last-60-days", action="store_true")
        parser2.add_argument("--dry-run", action="store_true")
        parser2.add_argument(
            "--sparse-threshold",
            type=int,
            default=GapDetector.DEFAULT_SPARSE_THRESHOLD,
        )
        args2 = parser2.parse_args()
        return cmd_reconcile(args2)


if __name__ == "__main__":
    sys.exit(main() or 0)
