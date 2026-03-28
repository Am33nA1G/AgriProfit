"""
Materialized View Refresh Endpoint

Add this to your analytics routes to manually refresh materialized views.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.auth.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/refresh-dashboard-views")
def refresh_dashboard_materialized_views(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Refresh all dashboard materialized views.
    
    This endpoint manually refreshes the materialized views used for
    dashboard analytics. Views are normally refreshed automatically
    every 15-30 minutes, but this endpoint allows manual refresh.
    
    Requires authentication (admin recommended).
    
    Returns:
        dict: Status of each view refresh with duration
    """
    import time
    
    results = {}
    
    # Refresh mv_market_summary
    try:
        start = time.time()
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_market_summary"))
        db.commit()
        duration = round(time.time() - start, 2)
        results['mv_market_summary'] = {'status': 'success', 'duration_seconds': duration}
    except Exception as e:
        results['mv_market_summary'] = {'status': 'error', 'error': str(e)}
    
    # Refresh mv_top_commodities_by_change
    try:
        start = time.time()
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_commodities_by_change"))
        db.commit()
        duration = round(time.time() - start, 2)
        results['mv_top_commodities_by_change'] = {'status': 'success', 'duration_seconds': duration}
    except Exception as e:
        results['mv_top_commodities_by_change'] = {'status': 'error', 'error': str(e)}
    
    # Refresh mv_recent_price_statistics
    try:
        start = time.time()
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_price_statistics"))
        db.commit()
        duration = round(time.time() - start, 2)
        results['mv_recent_price_statistics'] = {'status': 'success', 'duration_seconds': duration}
    except Exception as e:
        results['mv_recent_price_statistics'] = {'status': 'error', 'error': str(e)}
    
    return {
        'message': 'Materialized views refresh completed',
        'results': results,
        'total_duration_seconds': sum(
            r.get('duration_seconds', 0) 
            for r in results.values() 
            if r.get('status') == 'success'
        )
    }


# Add to app/analytics/routes.py:
# from app.analytics.refresh_views import router as refresh_router
# router.include_router(refresh_router, tags=["analytics"])


# MANUAL REFRESH VIA SQL:
# Connect to PostgreSQL and run:
# 
# REFRESH MATERIALIZED VIEW CONCURRENTLY mv_market_summary;
# REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_commodities_by_change;
# REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_price_statistics;
#
# Note: CONCURRENTLY allows reads while refreshing (requires unique index)


# AUTOMATED REFRESH (Recommended):
# Add to app/main.py startup event:
#
# from apscheduler.schedulers.background import BackgroundScheduler
# from app.analytics.refresh_views import refresh_dashboard_materialized_views
# 
# scheduler = BackgroundScheduler()
# 
# def refresh_views_job():
#     from app.database.session import SessionLocal
#     db = SessionLocal()
#     try:
#         # Refresh views every 15 minutes
#         db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_market_summary"))
#         db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_commodities_by_change"))
#         db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_price_statistics"))
#         db.commit()
#         print(f"✓ Refreshed materialized views at {datetime.now()}")
#     except Exception as e:
#         print(f"✗ Error refreshing views: {e}")
#     finally:
#         db.close()
# 
# scheduler.add_job(refresh_views_job, 'interval', minutes=15)
# scheduler.start()
