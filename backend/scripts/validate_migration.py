#!/usr/bin/env python3
"""
Post-migration validation script.

Checks row counts, data integrity, price statistics, and prints sample
records so you can verify the ETL completed correctly.

Usage:
    python scripts/validate_migration.py
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import func, text
from app.database.session import SessionLocal
from app.models.price_history import PriceHistory
from app.models.commodity import Commodity
from app.models.mandi import Mandi


def validate() -> None:
    db = SessionLocal()

    print("=" * 72)
    print("  MIGRATION VALIDATION")
    print("=" * 72)

    # ------------------------------------------------------------------
    # 1. Row counts
    # ------------------------------------------------------------------
    total = db.query(func.count(PriceHistory.id)).scalar() or 0
    n_commodities = db.query(func.count(Commodity.id)).scalar() or 0
    n_mandis = db.query(func.count(Mandi.id)).scalar() or 0

    print(f"\n  Total price_history rows : {total:>12,}")
    print(f"  Total commodities       : {n_commodities:>12,}")
    print(f"  Total mandis            : {n_mandis:>12,}")

    if total == 0:
        print("\n  No data found. Run the ETL script first.")
        db.close()
        return

    # ------------------------------------------------------------------
    # 2. Date range
    # ------------------------------------------------------------------
    min_date = db.query(func.min(PriceHistory.price_date)).scalar()
    max_date = db.query(func.max(PriceHistory.price_date)).scalar()
    print(f"\n  Date range : {min_date} to {max_date}")

    # ------------------------------------------------------------------
    # 3. Price statistics
    # ------------------------------------------------------------------
    avg_price = db.query(func.avg(PriceHistory.modal_price)).scalar()
    min_price = db.query(func.min(PriceHistory.modal_price)).scalar()
    max_price = db.query(func.max(PriceHistory.modal_price)).scalar()

    print(f"\n  Price statistics (modal_price):")
    print(f"    Average : {float(avg_price):>12,.2f}")
    print(f"    Min     : {float(min_price):>12,.2f}")
    print(f"    Max     : {float(max_price):>12,.2f}")

    # ------------------------------------------------------------------
    # 4. Rows per commodity (top 15)
    # ------------------------------------------------------------------
    rows_by_commodity = (
        db.query(Commodity.name, func.count(PriceHistory.id).label("cnt"))
        .join(PriceHistory, PriceHistory.commodity_id == Commodity.id)
        .group_by(Commodity.name)
        .order_by(text("cnt DESC"))
        .limit(15)
        .all()
    )

    print(f"\n  Top 15 commodities by row count:")
    for name, cnt in rows_by_commodity:
        print(f"    {name:30s} {cnt:>10,}")

    # ------------------------------------------------------------------
    # 5. Rows per mandi (top 10)
    # ------------------------------------------------------------------
    rows_by_mandi = (
        db.query(PriceHistory.mandi_name, func.count(PriceHistory.id).label("cnt"))
        .group_by(PriceHistory.mandi_name)
        .order_by(text("cnt DESC"))
        .limit(10)
        .all()
    )

    print(f"\n  Top 10 mandis by row count:")
    for name, cnt in rows_by_mandi:
        print(f"    {name:30s} {cnt:>10,}")

    # ------------------------------------------------------------------
    # 6. Null checks
    # ------------------------------------------------------------------
    null_commodity = db.query(func.count(PriceHistory.id)).filter(
        PriceHistory.commodity_id.is_(None)
    ).scalar() or 0
    null_mandi = db.query(func.count(PriceHistory.id)).filter(
        PriceHistory.mandi_id.is_(None)
    ).scalar() or 0
    null_modal = db.query(func.count(PriceHistory.id)).filter(
        PriceHistory.modal_price.is_(None)
    ).scalar() or 0

    print(f"\n  Null checks:")
    print(f"    Null commodity_id : {null_commodity:>10,}")
    print(f"    Null mandi_id     : {null_mandi:>10,}")
    print(f"    Null modal_price  : {null_modal:>10,}")

    # ------------------------------------------------------------------
    # 7. Sample records
    # ------------------------------------------------------------------
    samples = (
        db.query(PriceHistory)
        .order_by(PriceHistory.price_date.desc())
        .limit(5)
        .all()
    )

    print(f"\n  Sample records (most recent):")
    for s in samples:
        c_name = s.commodity.name if s.commodity else "?"
        print(
            f"    {s.price_date}  {c_name:20s}  "
            f"{s.mandi_name:20s}  modal={s.modal_price}"
        )

    # ------------------------------------------------------------------
    # 8. Duplicate check
    # ------------------------------------------------------------------
    dup_count = db.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT commodity_id, mandi_name, price_date, COUNT(*) as c
            FROM price_history
            GROUP BY commodity_id, mandi_name, price_date
            HAVING COUNT(*) > 1
        ) dupes
    """)).scalar() or 0

    print(f"\n  Duplicate (commodity_id, mandi_name, price_date) groups: {dup_count:,}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    issues = []
    if null_commodity > 0:
        issues.append(f"{null_commodity} null commodity_ids")
    if null_modal > 0:
        issues.append(f"{null_modal} null modal prices")
    if dup_count > 0:
        issues.append(f"{dup_count} duplicate groups")

    print("\n" + "=" * 72)
    if issues:
        print("  VALIDATION: ISSUES FOUND")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  VALIDATION: ALL CHECKS PASSED")
    print("=" * 72)

    db.close()


if __name__ == "__main__":
    validate()
