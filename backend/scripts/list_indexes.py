"""List all performance indexes in the database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database.session import SessionLocal

db = SessionLocal()

try:
    result = db.execute(text("""
        SELECT 
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexname::regclass)) as size
        FROM pg_indexes
        WHERE schemaname = 'public' 
          AND indexname LIKE 'ix_%'
        ORDER BY tablename, indexname
    """))
    
    print()
    print("=" * 90)
    print("PERFORMANCE INDEXES CREATED")
    print("=" * 90)
    print(f"{'Table':<25} {'Index Name':<45} {'Size':<10}")
    print("-" * 90)
    
    count = 0
    for row in result:
        print(f"{row[0]:<25} {row[1]:<45} {row[2]:<10}")
        count += 1
    
    print("-" * 90)
    print(f"Total: {count} indexes")
    print("=" * 90)
    print()
    
finally:
    db.close()
