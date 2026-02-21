"""
Verify Price Coverage - Lightweight verification of per-commodity data completeness.

Checks that key commodities have sufficient date coverage across
30, 60, and 90 day windows.

Usage:
    python scripts/verify_price_coverage.py
    python scripts/verify_price_coverage.py --min-coverage 80
    python scripts/verify_price_coverage.py --days 30

Exit codes:
    0 - All key commodities have sufficient coverage
    1 - One or more commodities have insufficient coverage
"""
import sys
import os
import argparse
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database.session import SessionLocal

# Key commodities that must have good coverage for the chart.
# Names use ILIKE %pattern% matching, so use the shortest unambiguous
# substring.  data.gov.in variants include:
#   "Arhar(Tur/Red Gram)(Whole)" and "Arhar (Tur/Red Gram)(Whole)"
#   "Black Gram(Urd Beans)(Whole)" (no "Urad" variant in recent data)
KEY_COMMODITIES = [
    "Rice", "Wheat", "Tomato", "Onion", "Potato",
    "Maize", "Soyabean", "Mustard", "Cotton", "Sugar",
    "Banana", "Apple", "Chillies", "Turmeric", "Garlic",
    "Ginger", "Arhar(Tur/Red Gram)", "Moong", "Black Gram(Urd", "Groundnut",
]


def get_max_date(db) -> date | None:
    """Get the latest date in price_history.

    Uses ORDER BY + LIMIT 1 for index efficiency on large tables.
    """
    result = db.execute(text(
        "SELECT price_date FROM price_history ORDER BY price_date DESC LIMIT 1"
    )).first()
    return result[0] if result else None


def check_commodity_coverage(
    db, commodity: str, start: date, end: date, total_days: int
) -> dict:
    """Check date coverage for a specific commodity."""
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

    return {
        "commodity": commodity,
        "days_with_data": days_with_data,
        "total_days": total_days,
        "coverage_pct": round(pct, 1),
    }


def check_date_gaps(db, start: date, end: date) -> list[tuple[date, date, int]]:
    """Find gaps (dates with ZERO records) in the given range."""
    result = db.execute(text("""
        SELECT DISTINCT price_date
        FROM price_history
        WHERE price_date >= :start AND price_date <= :end
        ORDER BY price_date
    """), {"start": start, "end": end})

    dates_with_data = {row[0] for row in result}
    gaps = []
    gap_start = None
    current = start

    while current <= end:
        if current not in dates_with_data:
            if gap_start is None:
                gap_start = current
        else:
            if gap_start is not None:
                gap_days = (current - gap_start).days
                gaps.append((gap_start, current - timedelta(days=1), gap_days))
                gap_start = None
        current += timedelta(days=1)

    if gap_start is not None:
        gap_days = (end - gap_start).days + 1
        gaps.append((gap_start, end, gap_days))

    return gaps


def main():
    parser = argparse.ArgumentParser(
        description="Verify per-commodity price coverage"
    )
    parser.add_argument(
        "--min-coverage", type=float, default=90.0,
        help="Minimum coverage %% to pass (default: 90)"
    )
    parser.add_argument(
        "--days", type=int, default=0,
        help="Check only this many days (0 = check 30, 60, 90)"
    )
    args = parser.parse_args()

    db = SessionLocal()

    try:
        max_date = get_max_date(db)
        if not max_date:
            print("ERROR: No data in price_history table!")
            return 1

        print("=" * 70)
        print("PRICE COVERAGE VERIFICATION")
        print("=" * 70)
        print(f"Latest data date: {max_date}")
        print(f"Minimum coverage: {args.min_coverage}%")
        print()

        windows = [args.days] if args.days > 0 else [30, 60, 90]
        all_passed = True

        for window in windows:
            start = max_date - timedelta(days=window)
            end = max_date
            total_days = window

            print(f"\n{'─' * 70}")
            print(f"LAST {window} DAYS ({start} to {end})")
            print(f"{'─' * 70}")

            # Check global gaps first
            gaps = check_date_gaps(db, start, end)
            if gaps:
                total_missing = sum(g[2] for g in gaps)
                print(f"\n  Global date gaps: {len(gaps)} gap(s), {total_missing} missing days")
                for gs, ge, gd in gaps[:5]:
                    print(f"    {gs} -> {ge} ({gd} days)")
                if len(gaps) > 5:
                    print(f"    ... and {len(gaps) - 5} more")
            else:
                print(f"\n  No global date gaps!")

            # Check per-commodity coverage
            print(f"\n  {'Commodity':<30} {'Days':>6} / {'Total':>5} {'Coverage':>10} {'Status':>8}")
            print(f"  {'-' * 65}")

            window_failures = []
            for commodity in KEY_COMMODITIES:
                cov = check_commodity_coverage(db, commodity, start, end, total_days)
                pct = cov["coverage_pct"]

                if pct >= args.min_coverage:
                    status = "PASS"
                elif pct >= 50:
                    status = "WARN"
                    window_failures.append(commodity)
                else:
                    status = "FAIL"
                    window_failures.append(commodity)

                print(
                    f"  {commodity:<30} {cov['days_with_data']:>6} / {total_days:>5} "
                    f"{pct:>8.1f}%  [{status}]"
                )

            if window_failures:
                all_passed = False
                print(f"\n  RESULT: {len(window_failures)} commodities below {args.min_coverage}% coverage")
            else:
                print(f"\n  RESULT: All commodities have >= {args.min_coverage}% coverage")

        # Overall summary
        print(f"\n{'=' * 70}")
        if all_passed:
            print("OVERALL: PASS - All key commodities have sufficient coverage")
        else:
            print("OVERALL: FAIL - Some commodities have insufficient coverage")
        print("=" * 70)

        return 0 if all_passed else 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
