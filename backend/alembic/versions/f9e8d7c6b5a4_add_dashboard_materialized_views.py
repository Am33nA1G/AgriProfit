"""add_dashboard_materialized_views

Revision ID: f9e8d7c6b5a4
Revises: acb7e03e5c47
Create Date: 2026-02-09 21:01:00.000000

Create materialized views for dashboard analytics to improve performance
from 30-90s to <1s for large datasets (25M+ rows).

Views created:
1. mv_market_summary - Overall market statistics
2. mv_top_commodities_by_change - Top commodities by price change
3. mv_recent_price_statistics - Recent price statistics by commodity/mandi

Refresh schedule: Every 15-30 minutes via background job
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9e8d7c6b5a4'
down_revision: Union[str, Sequence[str], None] = 'acb7e03e5c47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create materialized views for dashboard performance."""
    
    print("Creating dashboard materialized views...")
    
    # ============================================================
    # MATERIALIZED VIEW 1: Market Summary
    # ============================================================
    print("  - Creating mv_market_summary...")
    
    op.execute("""
        CREATE MATERIALIZED VIEW mv_market_summary AS
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
                (SELECT MAX(created_at) FROM price_history) as last_updated,
                NOW() as view_refreshed_at
        )
        SELECT * FROM counts;
    """)
    
    # Create index on the materialized view for faster access
    op.create_index(
        'ix_mv_market_summary_refreshed_at',
        'mv_market_summary',
        ['view_refreshed_at'],
        unique=False
    )
    
    # ============================================================
    # MATERIALIZED VIEW 2: Top Commodities by Price Change
    # ============================================================
    print("  - Creating mv_top_commodities_by_change...")
    
    op.execute("""
        CREATE MATERIALIZED VIEW mv_top_commodities_by_change AS
        WITH commodity_prices AS (
            SELECT
                ph.commodity_id,
                c.name,
                COUNT(*) OVER (PARTITION BY ph.commodity_id) AS record_count,
                FIRST_VALUE(ph.modal_price) OVER (
                    PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS first_price,
                LAST_VALUE(ph.modal_price) OVER (
                    PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_price,
                FIRST_VALUE(ph.price_date) OVER (
                    PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS first_date,
                LAST_VALUE(ph.price_date) OVER (
                    PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                ) AS last_date
            FROM price_history ph
            JOIN commodities c ON c.id = ph.commodity_id
            WHERE ph.price_date >= CURRENT_DATE - INTERVAL '30 days'
        ),
        changes AS (
            SELECT DISTINCT
                commodity_id,
                name,
                record_count,
                first_price,
                last_price,
                first_date,
                last_date,
                CASE WHEN first_price > 0
                    THEN ABS(((last_price - first_price) / first_price) * 100)
                    ELSE 0
                END AS price_change_percent,
                NOW() as view_refreshed_at
            FROM commodity_prices
            WHERE record_count >= 2
        )
        SELECT 
            commodity_id, 
            name, 
            record_count,
            first_price,
            last_price,
            first_date,
            last_date,
            price_change_percent,
            view_refreshed_at
        FROM changes
        ORDER BY price_change_percent DESC
        LIMIT 100;
    """)
    
    # Create indexes
    op.create_index(
        'ix_mv_top_commodities_commodity_id',
        'mv_top_commodities_by_change',
        ['commodity_id'],
        unique=False
    )
    
    op.create_index(
        'ix_mv_top_commodities_price_change',
        'mv_top_commodities_by_change',
        ['price_change_percent'],
        unique=False
    )
    
    # ============================================================
    # MATERIALIZED VIEW 3: Recent Price Statistics
    # ============================================================
    print("  - Creating mv_recent_price_statistics...")
    
    op.execute("""
        CREATE MATERIALIZED VIEW mv_recent_price_statistics AS
        WITH recent_prices AS (
            SELECT
                ph.commodity_id,
                c.name as commodity_name,
                ph.mandi_id,
                m.name as mandi_name,
                ph.modal_price,
                ph.price_date,
                ROW_NUMBER() OVER (
                    PARTITION BY ph.commodity_id, ph.mandi_id 
                    ORDER BY ph.price_date DESC
                ) as rn
            FROM price_history ph
            JOIN commodities c ON c.id = ph.commodity_id
            JOIN mandis m ON m.id = ph.mandi_id
            WHERE ph.price_date >= CURRENT_DATE - INTERVAL '90 days'
        ),
        first_last_prices AS (
            SELECT
                commodity_id,
                commodity_name,
                mandi_id,
                mandi_name,
                COUNT(*) as data_points,
                AVG(modal_price) as avg_price,
                MIN(modal_price) as min_price,
                MAX(modal_price) as max_price,
                FIRST_VALUE(modal_price) OVER (
                    PARTITION BY commodity_id, mandi_id 
                    ORDER BY price_date ASC
                ) as first_price,
                FIRST_VALUE(modal_price) OVER (
                    PARTITION BY commodity_id, mandi_id 
                    ORDER BY price_date DESC
                ) as last_price
            FROM recent_prices
            WHERE rn <= 90  -- Last 90 days
            GROUP BY commodity_id, commodity_name, mandi_id, mandi_name, modal_price, price_date
        )
        SELECT DISTINCT
            commodity_id,
            commodity_name,
            mandi_id,
            mandi_name,
            data_points,
            ROUND(avg_price::numeric, 2) as avg_price,
            ROUND(min_price::numeric, 2) as min_price,
            ROUND(max_price::numeric, 2) as max_price,
            CASE WHEN first_price > 0
                THEN ROUND((((last_price - first_price) / first_price) * 100)::numeric, 2)
                ELSE 0
            END as price_change_percent,
            NOW() as view_refreshed_at
        FROM first_last_prices
        WHERE data_points >= 5
        ORDER BY data_points DESC
        LIMIT 1000;
    """)
    
    # Create indexes
    op.create_index(
        'ix_mv_recent_stats_commodity_id',
        'mv_recent_price_statistics',
        ['commodity_id'],
        unique=False
    )
    
    op.create_index(
        'ix_mv_recent_stats_mandi_id',
        'mv_recent_price_statistics',
        ['mandi_id'],
        unique=False
    )
    
    op.create_index(
        'ix_mv_recent_stats_price_change',
        'mv_recent_price_statistics',
        ['price_change_percent'],
        unique=False
    )
    
    print("✓ Created 3 materialized views with indexes")
    print("  → mv_market_summary")
    print("  → mv_top_commodities_by_change")
    print("  → mv_recent_price_statistics")
    print("")
    print("⚠️  IMPORTANT: These views need to be refreshed periodically!")
    print("   Run: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_market_summary;")
    print("   Or use the background refresh job.")


def downgrade() -> None:
    """Drop materialized views."""
    
    print("Dropping dashboard materialized views...")
    
    # Drop indexes first
    op.drop_index('ix_mv_recent_stats_price_change', table_name='mv_recent_price_statistics')
    op.drop_index('ix_mv_recent_stats_mandi_id', table_name='mv_recent_price_statistics')
    op.drop_index('ix_mv_recent_stats_commodity_id', table_name='mv_recent_price_statistics')
    
    op.drop_index('ix_mv_top_commodities_price_change', table_name='mv_top_commodities_by_change')
    op.drop_index('ix_mv_top_commodities_commodity_id', table_name='mv_top_commodities_by_change')
    
    op.drop_index('ix_mv_market_summary_refreshed_at', table_name='mv_market_summary')
    
    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_recent_price_statistics;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_top_commodities_by_change;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_market_summary;")
    
    print("✓ Dropped all materialized views")
