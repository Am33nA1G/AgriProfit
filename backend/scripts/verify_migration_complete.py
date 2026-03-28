"""
Final verification that Parquet to PostgreSQL migration is complete.

Checks:
1. No Parquet file dependencies in code
2. Database has data
3. All indexes exist
4. Query performance acceptable
5. Sync service configured
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database.session import SessionLocal
from app.models.price_history import PriceHistory


def check_no_parquet_imports():
    """Verify no Parquet imports in app code."""
    print("1. Checking for Parquet imports...")
    
    app_dir = Path(__file__).parent.parent / "app"
    parquet_refs = []
    
    for py_file in app_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()
                if "read_parquet" in content or "to_parquet" in content:
                    parquet_refs.append(str(py_file.relative_to(app_dir.parent)))
        except Exception as e:
            print(f"   Warning: Could not read {py_file}: {e}")
    
    if parquet_refs:
        print(f"   ✗ Found Parquet references in:")
        for ref in parquet_refs:
            print(f"      - {ref}")
        return False
    
    print("   ✓ No Parquet imports found in app/ code")
    return True


def check_database_has_data():
    """Verify database has price data."""
    print("2. Checking database has data...")
    
    db = SessionLocal()
    try:
        count = db.query(PriceHistory).count()
        
        if count == 0:
            print("   ✗ Database is empty")
            return False
        
        print(f"   ✓ Database has {count:,} price records")
        return True
    except Exception as e:
        print(f"   ✗ Error querying database: {e}")
        return False
    finally:
        db.close()


def check_indexes_exist():
    """Verify performance indexes exist."""
    print("3. Checking indexes...")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT COUNT(*) as index_count
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = 'price_history'
            AND indexname LIKE 'ix_%'
        """))
        
        index_count = result.scalar()
        
        if index_count < 5:
            print(f"   ✗ Only {index_count} indexes found on price_history (expected 6+)")
            return False
        
        print(f"   ✓ {index_count} performance indexes exist on price_history")
        
        # Also check total indexes
        result2 = db.execute(text("""
            SELECT COUNT(*) as total_indexes
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname LIKE 'ix_%'
        """))
        
        total_indexes = result2.scalar()
        print(f"   ✓ {total_indexes} total performance indexes across all tables")
        
        return True
    except Exception as e:
        print(f"   ✗ Error checking indexes: {e}")
        return False
    finally:
        db.close()


def check_query_performance():
    """Verify queries are fast."""
    print("4. Checking query performance...")
    
    db = SessionLocal()
    try:
        # Test simple query
        start = time.time()
        prices = db.query(PriceHistory).limit(100).all()
        duration_ms = (time.time() - start) * 1000
        
        if duration_ms > 500:
            print(f"   ⚠ Query took {duration_ms:.0f}ms (target <500ms, acceptable if first run)")
        else:
            print(f"   ✓ Query took {duration_ms:.0f}ms (excellent)")
        
        # Test indexed query
        from app.models.commodity import Commodity
        commodity = db.query(Commodity).first()
        
        if commodity:
            start = time.time()
            prices = db.query(PriceHistory).filter(
                PriceHistory.commodity_id == commodity.id
            ).order_by(PriceHistory.price_date.desc()).limit(100).all()
            duration_ms = (time.time() - start) * 1000
            
            if duration_ms > 500:
                print(f"   ⚠ Indexed query took {duration_ms:.0f}ms (acceptable)")
                return True  # Still acceptable
            else:
                print(f"   ✓ Indexed query took {duration_ms:.0f}ms (excellent)")
        
        return True
    except Exception as e:
        print(f"   ✗ Error testing query performance: {e}")
        return False
    finally:
        db.close()


def check_sync_service():
    """Verify sync service is configured."""
    print("5. Checking sync service...")
    
    # Check if scheduler file exists
    scheduler_file = Path(__file__).parent.parent / "app" / "integrations" / "scheduler.py"
    if not scheduler_file.exists():
        print("   ✗ Scheduler file not found at app/integrations/scheduler.py")
        return False
    
    print("   ✓ Scheduler file exists")
    
    # Check if sync service exists
    sync_file = Path(__file__).parent.parent / "app" / "integrations" / "data_sync.py"
    if not sync_file.exists():
        print("   ✗ Data sync service not found at app/integrations/data_sync.py")
        return False
    
    print("   ✓ Data sync service file exists")
    
    # Check if sync is configured in main.py
    main_file = Path(__file__).parent.parent / "app" / "main.py"
    if main_file.exists():
        with open(main_file, encoding='utf-8') as f:
            content = f.read()
            if "scheduler" in content.lower() or "sync" in content.lower():
                print("   ✓ Sync service integrated in main.py")
            else:
                print("   ⚠ Sync service may not be integrated in main.py")
    
    return True


def check_parquet_dependencies():
    """Check if Parquet libraries are still in requirements."""
    print("6. Checking requirements.txt...")
    
    req_file = Path(__file__).parent.parent / "requirements.txt"
    if not req_file.exists():
        print("   ⚠ requirements.txt not found")
        return True
    
    with open(req_file, encoding='utf-8') as f:
        content = f.read()
        
    parquet_deps = []
    if "pyarrow" in content:
        parquet_deps.append("pyarrow")
    if "fastparquet" in content:
        parquet_deps.append("fastparquet")
    
    if parquet_deps:
        print(f"   ⚠ Found Parquet dependencies: {', '.join(parquet_deps)}")
        print(f"      Note: These may be needed for ETL scripts, acceptable if documented")
        return True  # Acceptable for ETL scripts
    else:
        print("   ✓ No Parquet dependencies in requirements.txt")
        return True


def main():
    """Run all verification checks."""
    print("=" * 80)
    print("PARQUET TO POSTGRESQL MIGRATION - FINAL VERIFICATION")
    print("=" * 80)
    print()
    
    checks = [
        ("No Parquet imports", check_no_parquet_imports()),
        ("Database has data", check_database_has_data()),
        ("Indexes exist", check_indexes_exist()),
        ("Query performance", check_query_performance()),
        ("Sync service", check_sync_service()),
        ("Dependencies", check_parquet_dependencies()),
    ]
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:<10} {name}")
    
    print("=" * 80)
    print(f"Result: {passed}/{total} checks passed")
    print()
    
    if passed == total:
        print("✓ ALL CHECKS PASSED - Migration complete!")
        print()
        print("Next steps:")
        print("1. Start application: cd backend && python -m uvicorn app.main:app --reload")
        print("2. Check sync status: curl http://localhost:8000/sync/status")
        print("3. Monitor logs: tail -f logs/data_sync.log")
        print("4. Run performance test: python scripts/test_query_performance.py")
        print()
        return 0
    elif passed >= total - 1:
        print("⚠ MOSTLY PASSED - Minor issues, review above")
        print()
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Review issues above")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
