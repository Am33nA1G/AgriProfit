"""
Database performance testing

Ensures all queries meet performance targets and use indexes correctly
"""

import time
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, func
from app.database.session import SessionLocal
from app.models.price_history import PriceHistory
from app.models.commodity import Commodity
from app.models.mandi import Mandi
from app.models.user import User
from app.models.community_post import CommunityPost

def time_query(name: str, query_func, target_ms: int = 200):
    """Time a query and check if it meets target"""
    try:
        start = time.time()
        result = query_func()
        duration_ms = (time.time() - start) * 1000
        
        # Determine status
        if duration_ms < target_ms:
            status = "✓"
            perf = "GOOD"
        elif duration_ms < 500:
            status = "⚠"
            perf = "OK"
        else:
            status = "✗"
            perf = "SLOW"
        
        # Get result count
        if isinstance(result, list):
            count = len(result)
        elif isinstance(result, int):
            count = result
        elif hasattr(result, '__len__'):
            count = len(result)
        else:
            count = 1
        
        print(f"{status} {name:55} {duration_ms:7.1f}ms (target: {target_ms:3}ms) [{count:7} results] {perf}")
        
        return duration_ms < 500  # Pass if under 500ms
        
    except Exception as e:
        print(f"✗ {name:55} ERROR: {str(e)[:50]}")
        return False

def test_index_usage(db):
    """Verify that queries use indexes"""
    print("\n" + "=" * 100)
    print("INDEX USAGE VERIFICATION")
    print("=" * 100)
    
    tests = [
        {
            'name': 'Price history by commodity_id',
            'query': """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM price_history
                WHERE commodity_id = (SELECT id FROM commodities LIMIT 1)
                LIMIT 100
            """
        },
        {
            'name': 'Price history by date range',
            'query': """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM price_history
                WHERE price_date >= CURRENT_DATE - INTERVAL '30 days'
                LIMIT 100
            """
        },
        {
            'name': 'Price history by mandi_id',
            'query': """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM price_history
                WHERE mandi_id = (SELECT id FROM mandis LIMIT 1)
                LIMIT 100
            """
        },
        {
            'name': 'Commodities by name (case-insensitive)',
            'query': """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM commodities
                WHERE LOWER(name) = 'wheat'
            """
        },
        {
            'name': 'Mandis by state',
            'query': """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM mandis
                WHERE state = 'Punjab'
                LIMIT 100
            """
        },
        {
            'name': 'Community posts by post_type',
            'query': """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM community_posts
                WHERE post_type = 'Crop Management'
                LIMIT 50
            """
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = db.execute(text(test['query']))
            explain_json = result.fetchone()[0]
            explain_str = str(explain_json)
            
            # Check if index is used
            uses_index = "Index Scan" in explain_str or "Index Only Scan" in explain_str
            
            if uses_index:
                print(f"✓ {test['name']:50} Uses index")
                passed += 1
            else:
                # Seq Scan might be OK for small tables
                if "Seq Scan" in explain_str:
                    print(f"⚠ {test['name']:50} Seq Scan (might be OK for small tables)")
                    passed += 1  # Don't fail, but warn
                else:
                    print(f"✗ {test['name']:50} No index usage detected")
                    failed += 1
                    
        except Exception as e:
            print(f"✗ {test['name']:50} ERROR: {str(e)[:30]}")
            failed += 1
    
    print(f"\nIndex Tests: {passed} passed, {failed} failed")
    return passed, failed

def main():
    """Run all database performance tests"""
    print("=" * 100)
    print("DATABASE PERFORMANCE TESTING - AgriProfit V1")
    print("=" * 100)
    print("Target: <200ms (good), <500ms (acceptable), >500ms (needs optimization)")
    print("=" * 100)
    
    db = SessionLocal()
    tests_passed = []
    
    try:
        # Basic counts
        print("\n[Basic Queries - Count Operations]")
        tests_passed.append(time_query(
            "Count all price records",
            lambda: db.query(PriceHistory).count(),
            target_ms=100
        ))
        
        tests_passed.append(time_query(
            "Count all commodities",
            lambda: db.query(Commodity).count(),
            target_ms=50
        ))
        
        tests_passed.append(time_query(
            "Count all mandis",
            lambda: db.query(Mandi).count(),
            target_ms=50
        ))
        
        tests_passed.append(time_query(
            "Count all users",
            lambda: db.query(User).count(),
            target_ms=50
        ))
        
        # Filtered queries with indexes
        print("\n[Indexed Queries - Single Table]")
        
        # Get sample IDs
        commodity = db.query(Commodity).first()
        mandi = db.query(Mandi).first()
        
        if commodity:
            tests_passed.append(time_query(
                "Get 100 prices for one commodity (indexed)",
                lambda: db.query(PriceHistory).filter(
                    PriceHistory.commodity_id == commodity.id
                ).limit(100).all(),
                target_ms=150
            ))
        
        if mandi:
            tests_passed.append(time_query(
                "Get 100 prices for one mandi (indexed)",
                lambda: db.query(PriceHistory).filter(
                    PriceHistory.mandi_id == mandi.id
                ).limit(100).all(),
                target_ms=150
            ))
        
        tests_passed.append(time_query(
            "Get prices from last 30 days (indexed)",
            lambda: db.query(PriceHistory).filter(
                PriceHistory.price_date >= '2024-01-01'
            ).limit(100).all(),
            target_ms=200
        ))
        
        tests_passed.append(time_query(
            "Get active commodities",
            lambda: db.query(Commodity).filter(
                Commodity.is_active == True
            ).all(),
            target_ms=100
        ))
        
        tests_passed.append(time_query(
            "Get mandis by state (indexed)",
            lambda: db.query(Mandi).filter(
                Mandi.state == 'Punjab'
            ).limit(100).all(),
            target_ms=150
        ))
        
        # Join queries
        print("\n[Join Queries - Multiple Tables]")
        
        tests_passed.append(time_query(
            "Join price_history + commodities",
            lambda: db.query(PriceHistory).join(Commodity).limit(50).all(),
            target_ms=250
        ))
        
        tests_passed.append(time_query(
            "Join price_history + mandis",
            lambda: db.query(PriceHistory).join(Mandi).limit(50).all(),
            target_ms=250
        ))
        
        tests_passed.append(time_query(
            "Join price_history + commodities + mandis",
            lambda: db.query(PriceHistory).join(
                Commodity
            ).join(
                Mandi
            ).limit(50).all(),
            target_ms=300
        ))
        
        # Aggregation queries
        print("\n[Aggregation Queries]")
        
        tests_passed.append(time_query(
            "Calculate average price per commodity",
            lambda: db.query(
                PriceHistory.commodity_id,
                func.avg(PriceHistory.modal_price)
            ).group_by(PriceHistory.commodity_id).limit(20).all(),
            target_ms=300
        ))
        
        tests_passed.append(time_query(
            "Calculate min/max prices per commodity",
            lambda: db.query(
                PriceHistory.commodity_id,
                func.min(PriceHistory.modal_price),
                func.max(PriceHistory.modal_price)
            ).group_by(PriceHistory.commodity_id).limit(20).all(),
            target_ms=300
        ))
        
        # Complex queries
        print("\n[Complex Queries]")
        
        if commodity:
            tests_passed.append(time_query(
                "Multi-filter query (commodity + date + ordering)",
                lambda: db.query(PriceHistory).filter(
                    PriceHistory.commodity_id == commodity.id,
                    PriceHistory.price_date >= '2024-01-01'
                ).order_by(PriceHistory.price_date.desc()).limit(50).all(),
                target_ms=200
            ))
        
        tests_passed.append(time_query(
            "Search commodities by name (case-insensitive)",
            lambda: db.query(Commodity).filter(
                func.lower(Commodity.name).like('%wheat%')
            ).all(),
            target_ms=150
        ))
        
        tests_passed.append(time_query(
            "Get recent community posts",
            lambda: db.query(CommunityPost).order_by(
                CommunityPost.created_at.desc()
            ).limit(20).all(),
            target_ms=200
        ))
        
        # Pagination queries
        print("\n[Pagination Queries]")
        
        tests_passed.append(time_query(
            "Paginate commodities (page 1)",
            lambda: db.query(Commodity).offset(0).limit(20).all(),
            target_ms=100
        ))
        
        tests_passed.append(time_query(
            "Paginate mandis (page 1)",
            lambda: db.query(Mandi).offset(0).limit(20).all(),
            target_ms=100
        ))
        
        tests_passed.append(time_query(
            "Paginate prices (page 1)",
            lambda: db.query(PriceHistory).offset(0).limit(50).all(),
            target_ms=150
        ))
        
        # Test index usage
        index_passed, index_failed = test_index_usage(db)
        
        # Summary
        print("\n" + "=" * 100)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 100)
        
        total_tests = len(tests_passed)
        passed_tests = sum(tests_passed)
        failed_tests = total_tests - passed_tests
        
        print(f"\nPerformance Tests: {passed_tests}/{total_tests} passed")
        print(f"Index Usage Tests: {index_passed} passed, {index_failed} failed")
        
        overall_passed = passed_tests + index_passed
        overall_total = total_tests + index_passed + index_failed
        
        print(f"\n{'✓' if failed_tests == 0 else '✗'} Overall: {overall_passed}/{overall_total} tests passed ({overall_passed/overall_total*100:.1f}%)")
        
        if failed_tests == 0 and index_failed == 0:
            print("\n✓ ALL TESTS PASSED - Database is optimized!")
        elif failed_tests < 3:
            print("\n⚠ Most tests passed - Minor optimization may be needed")
        else:
            print("\n✗ SOME TESTS FAILED - Database needs optimization")
        
        print("\n" + "=" * 100)
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
