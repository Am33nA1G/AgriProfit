"""
Comprehensive Database Consistency Audit for AgriProfit
Identifies gaps, anomalies, and missing data in the database.

Usage:
    cd backend
    python scripts/audit_database_consistency.py
"""
import sys
import json
from pathlib import Path

# Windows console encoding fix
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend root to path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, date, timedelta
from collections import defaultdict

from sqlalchemy import func, distinct, text as sa_text
from app.database.session import SessionLocal
from app.models import Commodity, Mandi, PriceHistory, User, Inventory, Sale


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def approximate_count(db, table_name: str) -> int:
    """Fast approximate row count via pg_class (avoids full table scan)."""
    row = db.execute(
        sa_text("SELECT reltuples::bigint FROM pg_class WHERE relname = :t"),
        {"t": table_name},
    ).first()
    return int(row[0]) if row and row[0] > 0 else 0


def find_date_gaps(db, start_date: date, end_date: date):
    """Return a list of (gap_start, gap_end, gap_days) for missing dates."""

    rows = (
        db.query(distinct(PriceHistory.price_date))
        .filter(PriceHistory.price_date.between(start_date, end_date))
        .all()
    )
    dates_with_data = {r[0] for r in rows}

    gaps = []
    gap_start = None
    current = start_date

    while current <= end_date:
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
        gap_days = (end_date - gap_start).days + 1
        gaps.append((gap_start, end_date, gap_days))

    return gaps


def check_sparse_commodities(db, total_days: int, threshold_pct: float = 50.0):
    """Return commodities whose date coverage is below *threshold_pct*."""
    results = (
        db.query(
            Commodity.id,
            Commodity.name,
            func.count(distinct(PriceHistory.price_date)).label("day_cnt"),
        )
        .outerjoin(PriceHistory, PriceHistory.commodity_id == Commodity.id)
        .group_by(Commodity.id, Commodity.name)
        .all()
    )
    sparse = []
    for cid, cname, day_cnt in results:
        if day_cnt and day_cnt > 0:
            pct = (day_cnt / total_days) * 100
            if pct < threshold_pct:
                sparse.append((str(cid), cname, round(pct, 1)))
    return sorted(sparse, key=lambda x: x[2])


def check_sparse_mandis(db, total_days: int, threshold_pct: float = 50.0):
    """Return mandis whose date coverage is below *threshold_pct*."""
    results = (
        db.query(
            Mandi.id,
            Mandi.name,
            func.count(distinct(PriceHistory.price_date)).label("day_cnt"),
        )
        .outerjoin(PriceHistory, PriceHistory.mandi_id == Mandi.id)
        .group_by(Mandi.id, Mandi.name)
        .all()
    )
    sparse = []
    for mid, mname, day_cnt in results:
        if day_cnt and day_cnt > 0:
            pct = (day_cnt / total_days) * 100
            if pct < threshold_pct:
                sparse.append((str(mid), mname, round(pct, 1)))
    return sorted(sparse, key=lambda x: x[2])


# ---------------------------------------------------------------------------
# Generate detailed gap report (saved as JSON)
# ---------------------------------------------------------------------------

def generate_gap_report(db, date_range_min, date_range_max):
    report = {
        "generated_at": datetime.now().isoformat(),
        "date_range": {
            "min": str(date_range_min),
            "max": str(date_range_max),
        },
        "date_gaps": [],
        "commodity_gaps": [],
        "mandi_gaps": [],
        "summary": {},
    }

    # Date gaps
    if date_range_min:
        gaps = find_date_gaps(db, date_range_min, date_range_max)
        report["date_gaps"] = [
            {"start": str(g[0]), "end": str(g[1]), "days": g[2]} for g in gaps
        ]

    # Commodities with zero prices
    sub = db.query(distinct(PriceHistory.commodity_id)).subquery()
    missing_commodities = (
        db.query(Commodity)
        .filter(~Commodity.id.in_(db.query(sub.c[0])))
        .all()
    )
    report["commodity_gaps"] = [
        {"id": str(c.id), "name": c.name, "category": c.category or "Unknown"}
        for c in missing_commodities
    ]

    # Mandis with zero prices (using mandi_id which is nullable)
    sub2 = (
        db.query(distinct(PriceHistory.mandi_id))
        .filter(PriceHistory.mandi_id.isnot(None))
        .subquery()
    )
    missing_mandis = (
        db.query(Mandi)
        .filter(~Mandi.id.in_(db.query(sub2.c[0])))
        .all()
    )
    report["mandi_gaps"] = [
        {"id": str(m.id), "name": m.name, "district": m.district, "state": m.state}
        for m in missing_mandis
    ]

    report["summary"] = {
        "total_date_gaps": len(report["date_gaps"]),
        "total_days_missing": sum(g["days"] for g in report["date_gaps"]),
        "commodities_without_prices": len(report["commodity_gaps"]),
        "mandis_without_prices": len(report["mandi_gaps"]),
    }

    return report


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def audit_database():
    print("=" * 80)
    print("  DATABASE CONSISTENCY AUDIT  -  AgriProfit")
    print("=" * 80)
    print(f"  Timestamp: {datetime.now()}\n")

    db = SessionLocal()
    issues: list[str] = []

    try:
        # ---- 1. Table Row Counts ----------------------------------------
        print("1. TABLE ROW COUNTS")
        print("-" * 80)

        exact_tables = {
            "commodities": db.query(func.count(Commodity.id)).scalar(),
            "mandis": db.query(func.count(Mandi.id)).scalar(),
            "users": db.query(func.count(User.id)).scalar(),
            "inventory": db.query(func.count(Inventory.id)).scalar(),
            "sales": db.query(func.count(Sale.id)).scalar(),
        }
        # Use approximate count for price_history (huge table)
        price_approx = approximate_count(db, "price_history")

        for tbl, cnt in exact_tables.items():
            print(f"   {tbl:25s} {cnt:>12,}")
            if tbl in ("commodities", "mandis") and cnt == 0:
                issues.append(f"CRITICAL: {tbl} table is empty")

        print(f"   {'price_history (approx)':25s} {price_approx:>12,}")

        if price_approx == 0:
            issues.append("CRITICAL: price_history table is empty")

        # ---- 2. Date Range Analysis --------------------------------------
        print("\n2. DATE RANGE ANALYSIS")
        print("-" * 80)

        row = db.query(
            func.min(PriceHistory.price_date).label("mn"),
            func.max(PriceHistory.price_date).label("mx"),
        ).first()

        date_min, date_max = row.mn, row.mx

        if date_min and date_max:
            total_days = (date_max - date_min).days + 1
            print(f"   Earliest record : {date_min}")
            print(f"   Latest record   : {date_max}")
            print(f"   Span            : {total_days:,} calendar days")

            # Date gaps
            gaps = find_date_gaps(db, date_min, date_max)
            if gaps:
                total_gap_days = sum(g[2] for g in gaps)
                print(f"\n   WARNING: {len(gaps)} date gap(s) totalling {total_gap_days:,} missing days")
                for gs, ge, gd in gaps[:15]:
                    print(f"      {gs}  ->  {ge}  ({gd} day{'s' if gd != 1 else ''})")
                    issues.append(f"Date gap: {gs} to {ge} ({gd} days)")
                if len(gaps) > 15:
                    print(f"      ... and {len(gaps) - 15} more gap(s)")
            else:
                print("   OK: No date gaps found")
        else:
            print("   ERROR: No price data in database")
            issues.append("No price data exists")
            date_min = date_max = None
            total_days = 0

        # ---- 3. Commodity Coverage ----------------------------------------
        print("\n3. COMMODITY COVERAGE")
        print("-" * 80)

        total_commodities = exact_tables["commodities"]
        commodities_with_prices = db.query(
            func.count(distinct(PriceHistory.commodity_id))
        ).scalar()

        print(f"   Total commodities         : {total_commodities}")
        print(f"   With price data           : {commodities_with_prices}")

        if total_commodities > commodities_with_prices:
            diff = total_commodities - commodities_with_prices
            print(f"   WARNING: {diff} commodities have NO price data")

            sub = db.query(distinct(PriceHistory.commodity_id)).subquery()
            missing = (
                db.query(Commodity.name)
                .filter(~Commodity.id.in_(db.query(sub.c[0])))
                .limit(15)
                .all()
            )
            for (n,) in missing:
                print(f"      - {n}")
                issues.append(f"Commodity '{n}' has no price data")

        if total_days > 0:
            sparse = check_sparse_commodities(db, total_days)
            if sparse:
                print(f"\n   {len(sparse)} commodities with <50% date coverage:")
                for _, name, pct in sparse[:10]:
                    print(f"      - {name}: {pct:.1f}%")

        # ---- 4. Mandi Coverage -------------------------------------------
        print("\n4. MANDI COVERAGE")
        print("-" * 80)

        total_mandis = exact_tables["mandis"]
        mandis_with_prices = (
            db.query(func.count(distinct(PriceHistory.mandi_id)))
            .filter(PriceHistory.mandi_id.isnot(None))
            .scalar()
        )

        print(f"   Total mandis              : {total_mandis}")
        print(f"   With price data           : {mandis_with_prices}")

        if total_mandis > mandis_with_prices:
            diff = total_mandis - mandis_with_prices
            print(f"   WARNING: {diff} mandis have NO price data")

            sub2 = (
                db.query(distinct(PriceHistory.mandi_id))
                .filter(PriceHistory.mandi_id.isnot(None))
                .subquery()
            )
            missing_m = (
                db.query(Mandi.name, Mandi.district, Mandi.state)
                .filter(~Mandi.id.in_(db.query(sub2.c[0])))
                .limit(10)
                .all()
            )
            for n, d, s in missing_m:
                print(f"      - {n}, {d}, {s}")
                issues.append(f"Mandi '{n}' ({d}, {s}) has no price data")

        # ---- 5. Data Quality Checks --------------------------------------
        print("\n5. DATA QUALITY CHECKS")
        print("-" * 80)

        # Invalid modal prices (using bounded date query for speed)
        invalid_cnt = (
            db.query(func.count(PriceHistory.id))
            .filter(
                (PriceHistory.modal_price <= 0)
                | (PriceHistory.modal_price > 1_000_000)
            )
            .scalar()
        )
        if invalid_cnt:
            print(f"   WARNING: {invalid_cnt:,} records with invalid modal_price (<=0 or >1M)")
            issues.append(f"{invalid_cnt} invalid modal_price records")
        else:
            print("   OK: All modal prices are valid (>0 and <=1M)")

        # Null mandi_id ratio
        null_mandi_cnt = (
            db.query(func.count(PriceHistory.id))
            .filter(PriceHistory.mandi_id.is_(None))
            .scalar()
        )
        print(f"   Records with NULL mandi_id: {null_mandi_cnt:,}")
        if null_mandi_cnt and price_approx > 0:
            pct = null_mandi_cnt / price_approx * 100
            print(f"   ({pct:.1f}% of total)")

        # ---- 6. Geographic Coverage --------------------------------------
        print("\n6. GEOGRAPHIC COVERAGE")
        print("-" * 80)

        states = (
            db.query(Mandi.state, func.count(Mandi.id).label("cnt"))
            .group_by(Mandi.state)
            .order_by(func.count(Mandi.id).desc())
            .all()
        )
        print(f"   {len(states)} state(s) represented:")
        for state, cnt in states[:15]:
            print(f"      {state:30s} {cnt:>5} mandis")
        if len(states) > 15:
            print(f"      ... and {len(states) - 15} more state(s)")

        # ---- 7. Data Freshness -------------------------------------------
        print("\n7. DATA FRESHNESS")
        print("-" * 80)

        if date_max:
            days_old = (date.today() - date_max).days
            print(f"   Latest data : {date_max}  ({days_old} day(s) ago)")
            if days_old > 7:
                issues.append(f"Data is {days_old} days old - sync needed")
                print(f"   WARNING: Data is stale (>{7} days)")
            elif days_old > 1:
                print(f"   INFO: Consider running a sync")
            else:
                print(f"   OK: Data is current")

        # ---- 8. Generate gap report JSON ----------------------------------
        print("\n8. GENERATING GAP REPORT")
        print("-" * 80)

        report = generate_gap_report(db, date_min, date_max)
        report_path = Path(__file__).resolve().parent.parent / "database_gaps_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"   Saved to: {report_path}")

        # ---- Summary -----------------------------------------------------
        print("\n" + "=" * 80)
        print("  AUDIT SUMMARY")
        print("=" * 80)

        if issues:
            print(f"\n  Found {len(issues)} issue(s):\n")
            for i, issue in enumerate(issues[:25], 1):
                print(f"    {i:>3}. {issue}")
            if len(issues) > 25:
                print(f"\n    ... and {len(issues) - 25} more")
            print(f"\n  STATUS: DATABASE HAS CONSISTENCY ISSUES")
            return False
        else:
            print("\n  STATUS: Database is consistent and complete")
            return True

    finally:
        db.close()


if __name__ == "__main__":
    ok = audit_database()
    sys.exit(0 if ok else 1)
