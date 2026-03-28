"""
Materialized View Helper Functions for Analytics Service

These functions query materialized views for instant dashboard performance.
Add these to analytics/service.py to replace slow queries.
"""

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from datetime import datetime, timezone, timedelta
import time


def get_market_summary_from_mv(db_session):
    """Get market summary from materialized view (instant - <100ms).
    
    Falls back to original query if view doesn't exist.
    Returns tuple: (data_dict, used_materialized_view: bool)
    """
    # Try materialized view first
    try:
        query = text("SELECT * FROM mv_market_summary LIMIT 1")
        result = db_session.execute(query).fetchone()
        
        if result:
            return {
                'total_commodities': result[0] or 0,
                'total_mandis': result[1] or 0,
                'total_price_records': result[2] or 0,
                'total_forecasts': result[3] or 0,
                'total_posts': result[4] or 0,
                'total_users': result[5] or 0,
                'last_updated': result[6] if result[6] else datetime.now(timezone.utc),
                'view_refreshed_at': result[7] if len(result) > 7 else None,
            }, True
    except ProgrammingError:
        # View doesn't exist, fall back
        pass
    
    # Fallback to original query
    query = text("""
        WITH counts AS (
            SELECT 
                (SELECT COUNT(*) FROM commodities) as total_commodities,
                (SELECT COUNT(*) FROM mandis) as total_mandis,
                (SELECT COUNT(*) FROM price_history) as total_price_records,
                (SELECT COUNT(*) FROM price_forecasts 
                 WHERE forecast_date >= CURRENT_DATE) as total_forecasts,
                (SELECT COUNT(*) FROM community_posts 
                 WHERE deleted_at IS NULL) as total_posts,
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT MAX(created_at) FROM price_history) as last_updated
        )
        SELECT * FROM counts
    """)
    
    result = db_session.execute(query).fetchone()
    
    return {
        'total_commodities': result[0] or 0,
        'total_mandis': result[1] or 0,
        'total_price_records': result[2] or 0,
        'total_forecasts': result[3] or 0,
        'total_posts': result[4] or 0,
        'total_users': result[5] or 0,
        'last_updated': result[6] if result[6] else datetime.now(timezone.utc),
        'view_refreshed_at': None,
    }, False


def get_top_commodities_from_mv(db_session, limit=10):
    """Get top commodities by price change from materialized view.
    
    Returns list of dicts with commodity data.
    """
    try:
        query = text("""
            SELECT commodity_id, name, record_count, price_change_percent
            FROM mv_top_commodities_by_change
            ORDER BY price_change_percent DESC
            LIMIT :limit
        """)
        
        rows = db_session.execute(query, {"limit": limit}).fetchall()
        
        return [
            {
                'commodity_id': row[0],
                'name': row[1],
                'record_count': row[2],
                'price_change_percent': float(row[3]) if row[3] else 0.0,
            }
            for row in rows
        ], True
    except ProgrammingError:
        # View doesn't exist, return empty with fallback flag
        return [], False


# USAGE IN analytics/service.py:
#
# Replace get_market_summary() method with:
#
# def get_market_summary(self) -> MarketSummaryResponse:
#     """Get overall market summary statistics (INSTANT with materialized view)."""
#     from app.analytics.mv_helpers import get_market_summary_from_mv
#     
#     data, used_mv = get_market_summary_from_mv(self.db)
#     
#     # Handle timezone
#     last_updated = data['last_updated']
#     if last_updated and last_updated.tzinfo is None:
#         local_offset = time.timezone if not time.daylight else time.altzone
#         local_offset_hours = -local_offset / 3600
#         last_updated = last_updated.replace(tzinfo=timezone.utc)
#         last_updated = last_updated - timedelta(hours=local_offset_hours)
#     
#     # Calculate freshness
#     now = datetime.now(timezone.utc)
#     hours_since_update = (now - last_updated).total_seconds() / 3600
#     data_is_stale = hours_since_update > 24
#     
#     return MarketSummaryResponse(
#         total_commodities=data['total_commodities'],
#         total_mandis=data['total_mandis'],
#         total_price_records=data['total_price_records'],
#         total_forecasts=data['total_forecasts'],
#         total_posts=data['total_posts'],
#         total_users=data['total_users'],
#         last_updated=last_updated,
#         data_is_stale=data_is_stale,
#         hours_since_update=round(hours_since_update, 1),
#     )
