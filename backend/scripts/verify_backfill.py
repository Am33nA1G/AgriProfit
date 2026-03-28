"""
Verify Backfill Completeness

Checks database coverage after the backfill, identifies any remaining gaps,
and provides a summary report.

Usage:
    python scripts/verify_backfill.py
"""
import sys
import os
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.database.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("BACKFILL VERIFICATION REPORT")
        print("=" * 70)

        # Overall stats
        result = db.execute(text("SELECT COUNT(*) FROM price_history"))
        total = result.scalar()
        print(f"\nTotal price records: {total:,}")

        result = db.execute(text("SELECT COUNT(*) FROM commodities"))
        print(f"Total commodities: {result.scalar()}")
        result = db.execute(text("SELECT COUNT(*) FROM mandis"))
        print(f"Total mandis: {result.scalar()}")

        result = db.execute(text(
            "SELECT MIN(price_date), MAX(price_date) FROM price_history"
        ))
        row = result.fetchone()
        print(f"Date range: {row[0]} to {row[1]}")

        # Monthly summary for the gap period
        print("\n--- Monthly Summary (Oct 2025 - Feb 2026) ---")
        result = db.execute(text("""
            SELECT
                DATE_TRUNC('month', price_date) as month,
                COUNT(*) as records,
                COUNT(DISTINCT commodity_id) as commodities,
                COUNT(DISTINCT mandi_name) as mandis
            FROM price_history
            WHERE price_date >= '2025-10-01' AND price_date <= '2026-02-28'
            GROUP BY DATE_TRUNC('month', price_date)
            ORDER BY month
        """))
        for row in result:
            print(f"  {row[0].strftime('%Y-%m')}: {row[1]:>10,} records | "
                  f"{row[2]:>4} commodities | {row[3]:>5} mandis")

        # Daily coverage check
        print("\n--- Daily Coverage (Oct 31, 2025 - Feb 9, 2026) ---")
        result = db.execute(text("""
            SELECT price_date, COUNT(*) as cnt
            FROM price_history
            WHERE price_date >= '2025-10-31' AND price_date <= '2026-02-09'
            GROUP BY price_date
            ORDER BY price_date
        """))

        daily_data = {row[0]: row[1] for row in result}

        # Check each date
        start = date(2025, 10, 31)
        end = date(2026, 2, 9)
        current = start

        total_days = 0
        good_days = 0
        weak_days = 0
        missing_days = 0
        gaps = []

        while current <= end:
            total_days += 1
            count = daily_data.get(current, 0)

            if count >= 5000:
                good_days += 1
            elif count > 0:
                weak_days += 1
                gaps.append((current, count, "WEAK"))
            else:
                missing_days += 1
                gaps.append((current, 0, "MISSING"))

            current += timedelta(days=1)

        print(f"  Total days in range: {total_days}")
        print(f"  Days with good data (>=5000): {good_days}")
        print(f"  Days with weak data (<5000):  {weak_days}")
        print(f"  Days with no data:            {missing_days}")

        coverage_pct = good_days / total_days * 100 if total_days > 0 else 0
        print(f"  Coverage: {coverage_pct:.1f}%")

        if gaps:
            print(f"\n  Gaps/Weak days ({len(gaps)}):")
            for d, cnt, status in gaps[:30]:  # Show first 30
                print(f"    {d}: {cnt:>8,} records ({status})")
            if len(gaps) > 30:
                print(f"    ... and {len(gaps) - 30} more")

        # Data quality checks
        print("\n--- Data Quality Checks ---")

        # Check for suspicious prices
        result = db.execute(text("""
            SELECT COUNT(*) FROM price_history
            WHERE price_date >= '2025-10-31' AND price_date <= '2026-02-09'
            AND modal_price <= 0
        """))
        zero_prices = result.scalar()
        print(f"  Records with modal_price <= 0: {zero_prices}")

        result = db.execute(text("""
            SELECT COUNT(*) FROM price_history
            WHERE price_date >= '2025-10-31' AND price_date <= '2026-02-09'
            AND modal_price > 10000000
        """))
        extreme_prices = result.scalar()
        print(f"  Records with modal_price > 10M: {extreme_prices}")

        # Check for orphaned records
        result = db.execute(text("""
            SELECT COUNT(*) FROM price_history ph
            WHERE price_date >= '2025-10-31' AND price_date <= '2026-02-09'
            AND NOT EXISTS (
                SELECT 1 FROM commodities c WHERE c.id = ph.commodity_id
            )
        """))
        orphaned = result.scalar()
        print(f"  Orphaned records (no commodity): {orphaned}")

        # Top commodities in backfilled data
        print("\n--- Top 10 Commodities (backfilled period) ---")
        result = db.execute(text("""
            SELECT c.name, COUNT(*) as cnt
            FROM price_history ph
            JOIN commodities c ON c.id = ph.commodity_id
            WHERE ph.price_date >= '2025-10-31' AND ph.price_date <= '2026-02-09'
            GROUP BY c.name
            ORDER BY cnt DESC
            LIMIT 10
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]:,}")

        # Top states
        print("\n--- Top 10 States (backfilled period) ---")
        result = db.execute(text("""
            SELECT m.state, COUNT(*) as cnt
            FROM price_history ph
            JOIN mandis m ON m.id = ph.mandi_id
            WHERE ph.price_date >= '2025-10-31' AND ph.price_date <= '2026-02-09'
            GROUP BY m.state
            ORDER BY cnt DESC
            LIMIT 10
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]:,}")

        # Final verdict
        print("\n" + "=" * 70)
        if coverage_pct >= 90:
            print("VERDICT: PASS - Backfill coverage is excellent")
        elif coverage_pct >= 70:
            print("VERDICT: ACCEPTABLE - Some gaps remain, re-run backfill for missing dates")
        else:
            print("VERDICT: INCOMPLETE - Significant gaps remain")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
