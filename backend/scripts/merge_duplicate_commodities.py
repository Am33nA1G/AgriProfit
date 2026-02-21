"""
Merge duplicate commodities that differ only in spacing before parentheses.

The data.gov.in API changed naming conventions around Oct 2025:
  - Old: "Almond (Badam)" -> stopped getting data
  - New: "Almond(Badam)"  -> current data

This script:
1. Finds all such pairs
2. Moves price_history from old commodity to new commodity (ON CONFLICT skip)
3. Deactivates the old commodity
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://postgres:agriprofit@localhost:5433/agprofit')

from app.database.session import SessionLocal
from sqlalchemy import text

def find_duplicate_pairs(db):
    """Find commodity pairs that differ only in spacing before parentheses."""
    result = db.execute(text("""
        SELECT c1.id as old_id, c1.name as old_name,
               c2.id as new_id, c2.name as new_name,
               (SELECT MAX(price_date) FROM price_history WHERE commodity_id = c1.id) as old_latest,
               (SELECT MAX(price_date) FROM price_history WHERE commodity_id = c2.id) as new_latest,
               (SELECT COUNT(*) FROM price_history WHERE commodity_id = c1.id) as old_count,
               (SELECT COUNT(*) FROM price_history WHERE commodity_id = c2.id) as new_count
        FROM commodities c1
        JOIN commodities c2 ON REPLACE(REPLACE(REPLACE(c1.name, ' ', ''), '(', ''), ')', '')
                              = REPLACE(REPLACE(REPLACE(c2.name, ' ', ''), '(', ''), ')', '')
        WHERE c1.id != c2.id
        AND c1.is_active = true AND c2.is_active = true
        AND c1.name LIKE '%% (%%'
        AND c2.name LIKE '%%(%'
        AND c2.name NOT LIKE '%% (%'
        ORDER BY c1.name
    """)).fetchall()
    return result


def merge_pair(db, old_id, old_name, new_id, new_name, dry_run=True):
    """Merge price_history from old commodity into new commodity."""
    # Count records to move
    move_count = db.execute(text("""
        SELECT COUNT(*) FROM price_history
        WHERE commodity_id = :old_id
    """), {"old_id": old_id}).scalar()

    if dry_run:
        print(f"  Would move {move_count:,} records from '{old_name}' -> '{new_name}'")
        return move_count

    # Move records: update commodity_id, skip conflicts (same mandi+date already exists)
    # Use INSERT ... ON CONFLICT approach for safety
    moved = db.execute(text("""
        WITH moved AS (
            UPDATE price_history
            SET commodity_id = :new_id
            WHERE commodity_id = :old_id
            AND NOT EXISTS (
                SELECT 1 FROM price_history ph2
                WHERE ph2.commodity_id = :new_id
                AND ph2.mandi_name = price_history.mandi_name
                AND ph2.price_date = price_history.price_date
            )
            RETURNING id
        )
        SELECT COUNT(*) FROM moved
    """), {"old_id": old_id, "new_id": new_id}).scalar()

    # Delete remaining old records (duplicates that couldn't be moved)
    deleted = db.execute(text("""
        DELETE FROM price_history WHERE commodity_id = :old_id
    """), {"old_id": old_id}).rowcount

    # Deactivate old commodity
    db.execute(text("""
        UPDATE commodities SET is_active = false WHERE id = :old_id
    """), {"old_id": old_id})

    print(f"  Moved {moved:,} records, deleted {deleted:,} duplicates, deactivated '{old_name}'")
    return moved


def main():
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("=" * 70)
        print("DRY RUN - No changes will be made. Pass --execute to apply.")
        print("=" * 70)
    else:
        print("=" * 70)
        print("EXECUTING - Changes will be committed!")
        print("=" * 70)

    db = SessionLocal()

    try:
        pairs = find_duplicate_pairs(db)
        print(f"\nFound {len(pairs)} duplicate pairs to merge:\n")

        total_moved = 0
        for pair in pairs:
            old_id, old_name, new_id, new_name = pair.old_id, pair.old_name, pair.new_id, pair.new_name
            old_latest, new_latest = pair.old_latest, pair.new_latest
            old_count, new_count = pair.old_count, pair.new_count

            print(f"'{old_name}' (latest: {old_latest}, {old_count:,} records)")
            print(f"  -> '{new_name}' (latest: {new_latest}, {new_count:,} records)")

            moved = merge_pair(db, old_id, old_name, new_id, new_name, dry_run=dry_run)
            total_moved += moved
            print()

        if not dry_run:
            db.commit()
            print(f"\nDone! Merged {len(pairs)} pairs, moved {total_moved:,} total records.")
        else:
            print(f"\nDry run complete. Would merge {len(pairs)} pairs, move {total_moved:,} total records.")
            print("Run with --execute to apply changes.")

    except Exception as e:
        db.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
