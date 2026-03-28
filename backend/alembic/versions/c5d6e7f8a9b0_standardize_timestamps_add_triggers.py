"""standardize timestamps to timestamptz, add updated_at triggers, drop duplicate indexes

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-03-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All TIMESTAMP columns that need converting to TIMESTAMPTZ
TIMESTAMP_COLUMNS = [
    ("users", "created_at"),
    ("users", "updated_at"),
    ("users", "deleted_at"),
    ("users", "last_login"),
    ("commodities", "created_at"),
    ("commodities", "updated_at"),
    ("community_posts", "created_at"),
    ("community_posts", "updated_at"),
    ("community_posts", "deleted_at"),
    ("community_replies", "created_at"),
    ("community_likes", "created_at"),
    ("price_history", "created_at"),
    ("price_history", "updated_at"),
    ("price_forecasts", "created_at"),
    ("price_forecasts", "updated_at"),
    ("otp_requests", "expires_at"),
    ("otp_requests", "created_at"),
    ("mandis", "created_at"),
    ("mandis", "updated_at"),
    ("inventory", "created_at"),
    ("inventory", "updated_at"),
    ("notifications", "created_at"),
    ("notifications", "updated_at"),
    ("notifications", "read_at"),
    ("admin_actions", "created_at"),
    ("sales", "created_at"),
]

# Tables that have an updated_at column and need the trigger
UPDATED_AT_TABLES = [
    "users",
    "commodities",
    "community_posts",
    "price_history",
    "price_forecasts",
    "inventory",
    "notifications",
    "mandis",
]

# Duplicate indexes from the performance migration that overlap with model __table_args__
DUPLICATE_INDEXES = [
    ("ix_mandis_state_district", "mandis"),    # duplicates idx_mandis_state_district
    ("ix_users_district", "users"),            # duplicates idx_users_district
    ("ix_users_role", "users"),                # duplicates idx_users_role
]


def upgrade() -> None:
    """Convert TIMESTAMP to TIMESTAMPTZ, add updated_at triggers, drop duplicate indexes."""

    # 1. Drop materialized views that depend on timestamp columns (must happen before ALTER TYPE)
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_recent_stats_price_change"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_recent_stats_mandi_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_recent_stats_commodity_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_top_commodities_price_change"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_top_commodities_commodity_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_market_summary_refreshed_at"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_recent_price_statistics"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_top_commodities_by_change"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_market_summary"))

    # 2. Convert all TIMESTAMP columns to TIMESTAMPTZ
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN {column} '
                f'TYPE TIMESTAMPTZ USING {column} AT TIME ZONE \'UTC\''
            )
        )

    # 2. Create the trigger function
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    # 3. Apply the trigger to all tables with updated_at
    for table in UPDATED_AT_TABLES:
        op.execute(sa.text(
            f'CREATE TRIGGER trg_{table}_updated_at '
            f'BEFORE UPDATE ON {table} '
            f'FOR EACH ROW EXECUTE FUNCTION set_updated_at()'
        ))

    # 4. Drop duplicate indexes
    for index_name, table_name in DUPLICATE_INDEXES:
        op.drop_index(index_name, table_name=table_name)

    # 5. Recreate materialized views
    op.execute(sa.text("""
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
        SELECT * FROM counts
    """))
    op.create_index("ix_mv_market_summary_refreshed_at", "mv_market_summary", ["view_refreshed_at"])

    op.execute(sa.text("""
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
                commodity_id, name, record_count, first_price, last_price,
                first_date, last_date,
                CASE WHEN first_price > 0
                    THEN ABS(((last_price - first_price) / first_price) * 100)
                    ELSE 0
                END AS price_change_percent,
                NOW() as view_refreshed_at
            FROM commodity_prices
            WHERE record_count >= 2
        )
        SELECT commodity_id, name, record_count, first_price, last_price,
               first_date, last_date, price_change_percent, view_refreshed_at
        FROM changes
        ORDER BY price_change_percent DESC
        LIMIT 100
    """))
    op.create_index("ix_mv_top_commodities_commodity_id", "mv_top_commodities_by_change", ["commodity_id"])
    op.create_index("ix_mv_top_commodities_price_change", "mv_top_commodities_by_change", ["price_change_percent"])

    op.execute(sa.text("""
        CREATE MATERIALIZED VIEW mv_recent_price_statistics AS
        WITH recent_prices AS (
            SELECT
                ph.commodity_id, c.name as commodity_name,
                ph.mandi_id, m.name as mandi_name,
                ph.modal_price, ph.price_date,
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
                commodity_id, commodity_name, mandi_id, mandi_name,
                COUNT(*) as data_points,
                AVG(modal_price) as avg_price,
                MIN(modal_price) as min_price,
                MAX(modal_price) as max_price,
                FIRST_VALUE(modal_price) OVER (
                    PARTITION BY commodity_id, mandi_id ORDER BY price_date ASC
                ) as first_price,
                FIRST_VALUE(modal_price) OVER (
                    PARTITION BY commodity_id, mandi_id ORDER BY price_date DESC
                ) as last_price
            FROM recent_prices
            WHERE rn <= 90
            GROUP BY commodity_id, commodity_name, mandi_id, mandi_name, modal_price, price_date
        )
        SELECT DISTINCT
            commodity_id, commodity_name, mandi_id, mandi_name, data_points,
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
        LIMIT 1000
    """))
    op.create_index("ix_mv_recent_stats_commodity_id", "mv_recent_price_statistics", ["commodity_id"])
    op.create_index("ix_mv_recent_stats_mandi_id", "mv_recent_price_statistics", ["mandi_id"])
    op.create_index("ix_mv_recent_stats_price_change", "mv_recent_price_statistics", ["price_change_percent"])


def downgrade() -> None:
    """Revert: drop triggers, drop function, recreate duplicate indexes, convert back to TIMESTAMP."""

    # 1. Drop materialized views before reverting column types
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_recent_stats_price_change"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_recent_stats_mandi_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_recent_stats_commodity_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_top_commodities_price_change"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_top_commodities_commodity_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_market_summary_refreshed_at"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_recent_price_statistics"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_top_commodities_by_change"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_market_summary"))

    # 2. Drop triggers
    for table in UPDATED_AT_TABLES:
        op.execute(sa.text(f'DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}'))

    # 3. Drop the trigger function
    op.execute(sa.text('DROP FUNCTION IF EXISTS set_updated_at()'))

    # 4. Convert TIMESTAMPTZ back to TIMESTAMP
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP'
            )
        )

    # 5. Recreate duplicate indexes
    op.create_index("ix_mandis_state_district", "mandis", ["state", "district"])
    op.create_index("ix_users_district", "users", ["district"])
    op.create_index("ix_users_role", "users", ["role"])

    # 6. Recreate materialized views (without TIMESTAMPTZ columns)
    op.execute(sa.text("""
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
        SELECT * FROM counts
    """))
    op.create_index("ix_mv_market_summary_refreshed_at", "mv_market_summary", ["view_refreshed_at"])
    op.execute(sa.text("""
        CREATE MATERIALIZED VIEW mv_top_commodities_by_change AS
        WITH commodity_prices AS (
            SELECT ph.commodity_id, c.name,
                COUNT(*) OVER (PARTITION BY ph.commodity_id) AS record_count,
                FIRST_VALUE(ph.modal_price) OVER (PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_price,
                LAST_VALUE(ph.modal_price) OVER (PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_price,
                FIRST_VALUE(ph.price_date) OVER (PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_date,
                LAST_VALUE(ph.price_date) OVER (PARTITION BY ph.commodity_id ORDER BY ph.price_date ASC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_date
            FROM price_history ph JOIN commodities c ON c.id = ph.commodity_id
            WHERE ph.price_date >= CURRENT_DATE - INTERVAL '30 days'
        ),
        changes AS (
            SELECT DISTINCT commodity_id, name, record_count, first_price, last_price, first_date, last_date,
                CASE WHEN first_price > 0 THEN ABS(((last_price - first_price) / first_price) * 100) ELSE 0 END AS price_change_percent,
                NOW() as view_refreshed_at
            FROM commodity_prices WHERE record_count >= 2
        )
        SELECT commodity_id, name, record_count, first_price, last_price, first_date, last_date, price_change_percent, view_refreshed_at
        FROM changes ORDER BY price_change_percent DESC LIMIT 100
    """))
    op.create_index("ix_mv_top_commodities_commodity_id", "mv_top_commodities_by_change", ["commodity_id"])
    op.create_index("ix_mv_top_commodities_price_change", "mv_top_commodities_by_change", ["price_change_percent"])
    op.execute(sa.text("""
        CREATE MATERIALIZED VIEW mv_recent_price_statistics AS
        WITH recent_prices AS (
            SELECT ph.commodity_id, c.name as commodity_name, ph.mandi_id, m.name as mandi_name,
                ph.modal_price, ph.price_date,
                ROW_NUMBER() OVER (PARTITION BY ph.commodity_id, ph.mandi_id ORDER BY ph.price_date DESC) as rn
            FROM price_history ph JOIN commodities c ON c.id = ph.commodity_id JOIN mandis m ON m.id = ph.mandi_id
            WHERE ph.price_date >= CURRENT_DATE - INTERVAL '90 days'
        ),
        first_last_prices AS (
            SELECT commodity_id, commodity_name, mandi_id, mandi_name, COUNT(*) as data_points,
                AVG(modal_price) as avg_price, MIN(modal_price) as min_price, MAX(modal_price) as max_price,
                FIRST_VALUE(modal_price) OVER (PARTITION BY commodity_id, mandi_id ORDER BY price_date ASC) as first_price,
                FIRST_VALUE(modal_price) OVER (PARTITION BY commodity_id, mandi_id ORDER BY price_date DESC) as last_price
            FROM recent_prices WHERE rn <= 90
            GROUP BY commodity_id, commodity_name, mandi_id, mandi_name, modal_price, price_date
        )
        SELECT DISTINCT commodity_id, commodity_name, mandi_id, mandi_name, data_points,
            ROUND(avg_price::numeric, 2) as avg_price, ROUND(min_price::numeric, 2) as min_price,
            ROUND(max_price::numeric, 2) as max_price,
            CASE WHEN first_price > 0 THEN ROUND((((last_price - first_price) / first_price) * 100)::numeric, 2) ELSE 0 END as price_change_percent,
            NOW() as view_refreshed_at
        FROM first_last_prices WHERE data_points >= 5 ORDER BY data_points DESC LIMIT 1000
    """))
    op.create_index("ix_mv_recent_stats_commodity_id", "mv_recent_price_statistics", ["commodity_id"])
    op.create_index("ix_mv_recent_stats_mandi_id", "mv_recent_price_statistics", ["mandi_id"])
    op.create_index("ix_mv_recent_stats_price_change", "mv_recent_price_statistics", ["price_change_percent"])
