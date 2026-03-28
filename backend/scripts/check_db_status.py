"""Quick check of current database status."""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.database.session import SessionLocal

db = SessionLocal()
try:
    result = db.execute(text("SELECT COUNT(*) FROM price_history"))
    print(f"Total price_history: {result.scalar():,}")

    result = db.execute(text(
        "SELECT MIN(price_date), MAX(price_date) FROM price_history"
    ))
    row = result.fetchone()
    print(f"Date range: {row[0]} to {row[1]}")

    result = db.execute(text("""
        SELECT price_date, COUNT(*) as cnt
        FROM price_history
        WHERE price_date >= '2025-10-28' AND price_date <= '2026-02-10'
        GROUP BY price_date
        ORDER BY price_date
    """))
    print("\nDaily records (Oct 28, 2025 - Feb 10, 2026):")
    for row in result:
        marker = " <-- NEW" if row[1] > 10000 and row[0].month in (11,) else ""
        marker = " <-- BACKFILLED" if row[0].month == 11 and row[0].year == 2025 else marker
        print(f"  {row[0]}: {row[1]:>8,}{marker}")

    result = db.execute(text("SELECT COUNT(*) FROM commodities"))
    print(f"\nTotal commodities: {result.scalar()}")
    result = db.execute(text("SELECT COUNT(*) FROM mandis"))
    print(f"Total mandis: {result.scalar()}")

finally:
    db.close()
