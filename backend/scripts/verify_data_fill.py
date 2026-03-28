"""
Post-fill verification script for AgriProfit database.

Compares before/after statistics and checks that gaps have been closed.

Usage:
    cd backend
    python scripts/verify_data_fill.py
"""
import sys
import json
from pathlib import Path

# Windows console encoding fix
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, date
from sqlalchemy import func, distinct, text as sa_text
from app.database.session import SessionLocal
from app.models import Commodity, Mandi, PriceHistory


def approximate_count(db, table_name: str) -> int:
    row = db.execute(
        sa_text("SELECT reltuples::bigint FROM pg_class WHERE relname = :t"),
        {"t": table_name},
    ).first()
    return int(row[0]) if row and row[0] > 0 else 0


def verify():
    print("=" * 80)
    print("  DATA FILL VERIFICATION")
    print("=" * 80)
    print(f"  Timestamp: {datetime.now()}\n")

    db = SessionLocal()

    try:
        # ---- Overall statistics ------------------------------------------
        print("1. OVERALL STATISTICS")
        print("-" * 80)

        approx_total = approximate_count(db, "price_history")
        print(f"   Price records (approx) : {approx_total:>12,}")

        row = db.query(
            func.min(PriceHistory.price_date).label("mn"),
            func.max(PriceHistory.price_date).label("mx"),
        ).first()
        date_min, date_max = row.mn, row.mx

        print(f"   Earliest record        : {date_min}")
        print(f"   Latest record          : {date_max}")

        if date_min and date_max:
            span = (date_max - date_min).days + 1
            print(f"   Span                   : {span:>12,} days")

        # Coverage
        comm_with = db.query(func.count(distinct(PriceHistory.commodity_id))).scalar()
        mandi_with = (
            db.query(func.count(distinct(PriceHistory.mandi_id)))
            .filter(PriceHistory.mandi_id.isnot(None))
            .scalar()
        )
        total_comm = db.query(func.count(Commodity.id)).scalar()
        total_mandi = db.query(func.count(Mandi.id)).scalar()

        comm_pct = (comm_with / total_comm * 100) if total_comm else 0
        mandi_pct = (mandi_with / total_mandi * 100) if total_mandi else 0

        print(f"\n   Commodity coverage     : {comm_with}/{total_comm} ({comm_pct:.1f}%)")
        print(f"   Mandi coverage         : {mandi_with}/{total_mandi} ({mandi_pct:.1f}%)")

        # ---- Compare with pre-fill report --------------------------------
        print("\n2. COMPARISON WITH PRE-FILL REPORT")
        print("-" * 80)

        report_path = Path(__file__).resolve().parent.parent / "database_gaps_report.json"
        if report_path.exists():
            with open(report_path, encoding="utf-8") as f:
                old_report = json.load(f)

            old_summary = old_report.get("summary", {})
            print(f"   Pre-fill date gaps          : {old_summary.get('total_date_gaps', '?')}")
            print(f"   Pre-fill missing days       : {old_summary.get('total_days_missing', '?')}")
            print(f"   Pre-fill commodities w/o px : {old_summary.get('commodities_without_prices', '?')}")
            print(f"   Pre-fill mandis w/o px      : {old_summary.get('mandis_without_prices', '?')}")
        else:
            print("   (pre-fill report not found -- skipping comparison)")

        # ---- Re-check for remaining gaps ---------------------------------
        print("\n3. REMAINING DATE GAPS")
        print("-" * 80)

        if date_min and date_max:
            from scripts.audit_database_consistency import find_date_gaps
            remaining_gaps = find_date_gaps(db, date_min, date_max)

            if remaining_gaps:
                total_remaining = sum(g[2] for g in remaining_gaps)
                print(f"   WARNING: {len(remaining_gaps)} gap(s) remaining ({total_remaining} day(s))")
                for gs, ge, gd in remaining_gaps[:10]:
                    print(f"      {gs} -> {ge}  ({gd} day(s))")
                if len(remaining_gaps) > 10:
                    print(f"      ... and {len(remaining_gaps) - 10} more")
            else:
                print("   OK: No date gaps remaining")
        else:
            print("   SKIP: No data to check")

        # ---- Data freshness ----------------------------------------------
        print("\n4. DATA FRESHNESS")
        print("-" * 80)

        if date_max:
            days_old = (date.today() - date_max).days
            print(f"   Latest data is {days_old} day(s) old")
            if days_old <= 1:
                print("   OK: Data is current")
            elif days_old <= 7:
                print("   INFO: Acceptable, will be refreshed by next sync")
            else:
                print(f"   WARNING: Data is stale (>{7} days)")

        # ---- Final verdict -----------------------------------------------
        print("\n" + "=" * 80)
        print("  VERIFICATION RESULT")
        print("=" * 80)

        all_ok = True

        if date_min and date_max:
            remaining = find_date_gaps(db, date_min, date_max)
            if remaining:
                remaining_days = sum(g[2] for g in remaining)
                print(f"\n  PARTIAL: {len(remaining)} gap(s) remain ({remaining_days} day(s))")
                print("  Note: Gaps on weekends / market holidays are expected.")
                all_ok = False

        if comm_pct < 100:
            print(f"\n  INFO: {total_comm - comm_with} commodities still have no prices")

        if all_ok:
            print("\n  PASS: Database is in good shape for production")
        else:
            print("\n  INFO: Some gaps remain (may be normal for market holidays)")

    finally:
        db.close()


if __name__ == "__main__":
    verify()
