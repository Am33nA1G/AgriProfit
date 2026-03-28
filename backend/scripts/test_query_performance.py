"""Test query performance after adding indexes.

This script runs various queries against the database to verify that
indexes are working properly and queries execute in <200ms.
"""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database.session import SessionLocal
from app.models.price_history import PriceHistory
from app.models.commodity import Commodity
from app.models.mandi import Mandi
from app.models.community_post import CommunityPost


def time_query(name, query_func):
    """Time a query and print results."""
    db = SessionLocal()
    try:
        start = time.time()
        result = query_func(db)
        duration = (time.time() - start) * 1000  # Convert to ms
        
        count = len(result) if isinstance(result, list) else result
        
        # Status indicators
        if duration < 200:
            status = "✓ GOOD"
        elif duration < 500:
            status = "⚠ OK  "
        else:
            status = "✗ SLOW"
        
        print(f"{status} | {duration:7.2f}ms | {count:5} rows | {name}")
        
        return duration
    finally:
        db.close()


def main():
    """Run all performance tests."""
    print("=" * 90)
    print("QUERY PERFORMANCE TEST")
    print("Target: <200ms (GOOD), <500ms (OK), >500ms (SLOW - needs optimization)")
    print("=" * 90)
    print()
    
    total_duration = 0
    test_count = 0
    
    # ============================================================
    # PRICE HISTORY QUERIES
    # ============================================================
    
    print("PRICE HISTORY QUERIES (Most Critical)")
    print("-" * 90)
    
    # Test 1: Get prices for specific commodity
    def test1(db):
        commodity = db.query(Commodity).first()
        if commodity:
            return db.query(PriceHistory).filter(
                PriceHistory.commodity_id == commodity.id
            ).order_by(PriceHistory.price_date.desc()).limit(100).all()
        return []
    
    total_duration += time_query("Get 100 prices for commodity (indexed on commodity_id, price_date)", test1)
    test_count += 1
    
    # Test 2: Get prices for specific mandi
    def test2(db):
        mandi = db.query(Mandi).first()
        if mandi:
            return db.query(PriceHistory).filter(
                PriceHistory.mandi_id == mandi.id
            ).order_by(PriceHistory.price_date.desc()).limit(100).all()
        return []
    
    total_duration += time_query("Get 100 prices for mandi (indexed on mandi_id, price_date)", test2)
    test_count += 1
    
    # Test 3: Get prices for date range
    def test3(db):
        return db.query(PriceHistory).filter(
            PriceHistory.price_date >= '2025-01-01'
        ).order_by(PriceHistory.price_date.desc()).limit(100).all()
    
    total_duration += time_query("Get 100 prices from date (indexed on price_date)", test3)
    test_count += 1
    
    # Test 4: Complex commodity + mandi + date query
    def test4(db):
        commodity = db.query(Commodity).first()
        mandi = db.query(Mandi).first()
        if commodity and mandi:
            return db.query(PriceHistory).filter(
                PriceHistory.commodity_id == commodity.id,
                PriceHistory.mandi_id == mandi.id,
                PriceHistory.price_date >= '2025-01-01'
            ).order_by(PriceHistory.price_date.desc()).limit(50).all()
        return []
    
    total_duration += time_query("Commodity + mandi + date (indexed on all three)", test4)
    test_count += 1
    
    print()
    
    # ============================================================
    # COMMODITY QUERIES
    # ============================================================
    
    print("COMMODITY QUERIES")
    print("-" * 90)
    
    # Test 5: Search commodity by name (case-insensitive)
    def test5(db):
        return db.query(Commodity).filter(
            Commodity.name.ilike('%wheat%')
        ).all()
    
    total_duration += time_query("Search commodities by name (indexed on LOWER(name))", test5)
    test_count += 1
    
    # Test 6: Filter by category
    def test6(db):
        return db.query(Commodity).filter(
            Commodity.category == 'Grains'
        ).limit(100).all()
    
    total_duration += time_query("Filter commodities by category (indexed on category)", test6)
    test_count += 1
    
    # Test 7: Get active commodities
    def test7(db):
        return db.query(Commodity).filter(
            Commodity.is_active == True
        ).limit(100).all()
    
    total_duration += time_query("Get active commodities (indexed on is_active)", test7)
    test_count += 1
    
    print()
    
    # ============================================================
    # MANDI QUERIES
    # ============================================================
    
    print("MANDI QUERIES")
    print("-" * 90)
    
    # Test 8: Filter by state
    def test8(db):
        return db.query(Mandi).filter(
            Mandi.state == 'Punjab'
        ).limit(100).all()
    
    total_duration += time_query("Filter mandis by state (indexed on state)", test8)
    test_count += 1
    
    # Test 9: Filter by state + district
    def test9(db):
        return db.query(Mandi).filter(
            Mandi.state == 'Punjab',
            Mandi.district == 'Ludhiana'
        ).all()
    
    total_duration += time_query("Filter mandis by state + district (composite index)", test9)
    test_count += 1
    
    # Test 10: Search mandi by name
    def test10(db):
        return db.query(Mandi).filter(
            Mandi.name.ilike('%market%')
        ).limit(100).all()
    
    total_duration += time_query("Search mandis by name (indexed on LOWER(name))", test10)
    test_count += 1
    
    print()
    
    # ============================================================
    # COMMUNITY QUERIES
    # ============================================================
    
    print("COMMUNITY QUERIES")
    print("-" * 90)
    
    # Test 11: Get posts by post_type
    def test11(db):
        return db.query(CommunityPost).filter(
            CommunityPost.post_type == 'discussion'
        ).order_by(CommunityPost.created_at.desc()).limit(50).all()
    
    total_duration += time_query("Get posts by type (indexed on post_type, created_at)", test11)
    test_count += 1
    
    print()
    
    # ============================================================
    # JOIN QUERIES
    # ============================================================
    
    print("JOIN QUERIES")
    print("-" * 90)
    
    # Test 12: Join price history with commodity
    def test12(db):
        return db.query(PriceHistory).join(
            Commodity, PriceHistory.commodity_id == Commodity.id
        ).filter(
            Commodity.category == 'Grains'
        ).order_by(PriceHistory.price_date.desc()).limit(50).all()
    
    total_duration += time_query("Join prices + commodities (uses both indexes)", test12)
    test_count += 1
    
    # Test 13: Join price history with mandi
    def test13(db):
        return db.query(PriceHistory).join(
            Mandi, PriceHistory.mandi_id == Mandi.id
        ).filter(
            Mandi.state == 'Punjab'
        ).order_by(PriceHistory.price_date.desc()).limit(50).all()
    
    total_duration += time_query("Join prices + mandis (uses both indexes)", test13)
    test_count += 1
    
    print()
    
    # ============================================================
    # AGGREGATION QUERIES
    # ============================================================
    
    print("AGGREGATION QUERIES")
    print("-" * 90)
    
    # Test 14: Average price by commodity
    def test14(db):
        result = db.execute(text("""
            SELECT 
                commodity_id,
                AVG(modal_price) as avg_price,
                COUNT(*) as count
            FROM price_history
            WHERE price_date >= '2025-01-01'
            GROUP BY commodity_id
            LIMIT 50
        """))
        return result.fetchall()
    
    total_duration += time_query("Aggregation: avg price by commodity (uses date index)", test14)
    test_count += 1
    
    # Test 15: Count prices per mandi
    def test15(db):
        result = db.execute(text("""
            SELECT 
                mandi_id,
                COUNT(*) as price_count
            FROM price_history
            WHERE price_date >= '2025-01-01'
            GROUP BY mandi_id
            LIMIT 50
        """))
        return result.fetchall()
    
    total_duration += time_query("Aggregation: count by mandi (uses mandi_id, date indexes)", test15)
    test_count += 1
    
    print()
    print("=" * 90)
    
    # Summary
    avg_duration = total_duration / test_count if test_count > 0 else 0
    print(f"SUMMARY: {test_count} tests, Average: {avg_duration:.2f}ms")
    
    if avg_duration < 200:
        print("✓ EXCELLENT: All queries are fast!")
    elif avg_duration < 500:
        print("⚠ ACCEPTABLE: Most queries are reasonably fast")
    else:
        print("✗ NEEDS OPTIMIZATION: Queries are too slow")
    
    print("=" * 90)
    print()
    
    # ============================================================
    # CHECK INDEX USAGE
    # ============================================================
    
    print("CHECKING INDEX USAGE (EXPLAIN ANALYZE)")
    print("-" * 90)
    print()
    
    db = SessionLocal()
    try:
        # Check if commodity index is being used
        print("Query: SELECT FROM price_history WHERE commodity_id = ? ORDER BY price_date DESC")
        print()
        result = db.execute(text("""
            EXPLAIN (FORMAT TEXT)
            SELECT * FROM price_history
            WHERE commodity_id = (SELECT id FROM commodities LIMIT 1)
            ORDER BY price_date DESC
            LIMIT 100
        """))
        
        for row in result:
            line = row[0]
            if 'Index Scan' in line:
                print(f"✓ {line}")
            elif 'Seq Scan' in line:
                print(f"✗ {line} (WARNING: Not using index!)")
            else:
                print(f"  {line}")
        
        print()
        print("-" * 90)
        
        # If we see "Index Scan", indexes are working!
        # If we see "Seq Scan", indexes are NOT being used (problem!)
        
    finally:
        db.close()
    
    print()
    print("TIP: Look for 'Index Scan' in the explain output above.")
    print("     If you see 'Seq Scan', the index is not being used.")
    print()


if __name__ == "__main__":
    main()
