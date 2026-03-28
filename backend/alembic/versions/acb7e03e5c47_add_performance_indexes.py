"""add_performance_indexes

Revision ID: acb7e03e5c47
Revises: d0bc3dcef208
Create Date: 2026-02-06 16:41:34.646891

Add comprehensive performance indexes for all major tables to ensure
queries execute in <200ms. Focuses on:
- Foreign key lookups
- Date range queries
- Common filter combinations
- Text search patterns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acb7e03e5c47'
down_revision: Union[str, Sequence[str], None] = 'd0bc3dcef208'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes."""
    
    print("Creating performance indexes...")
    
    # ============================================================
    # PRICE_HISTORY TABLE INDEXES (Most Critical - Millions of Rows)
    # ============================================================
    
    print("  - Price history indexes...")
    
    # Index 1: Foreign key lookup for commodity
    op.create_index(
        'ix_price_history_commodity_id',
        'price_history',
        ['commodity_id'],
        unique=False
    )
    
    # Index 2: Foreign key lookup for mandi
    op.create_index(
        'ix_price_history_mandi_id',
        'price_history',
        ['mandi_id'],
        unique=False
    )
    
    # Index 3: Date range queries
    op.create_index(
        'ix_price_history_price_date',
        'price_history',
        ['price_date'],
        unique=False
    )
    
    # Index 4: Composite index for commodity + date (most common query)
    op.create_index(
        'ix_price_history_commodity_date',
        'price_history',
        ['commodity_id', 'price_date'],
        unique=False
    )
    
    # Index 5: Composite index for mandi + date
    op.create_index(
        'ix_price_history_mandi_date',
        'price_history',
        ['mandi_id', 'price_date'],
        unique=False
    )
    
    # Index 6: Composite index for commodity + mandi + date (specific lookups)
    op.create_index(
        'ix_price_history_commodity_mandi_date',
        'price_history',
        ['commodity_id', 'mandi_id', 'price_date'],
        unique=False
    )
    
    # ============================================================
    # COMMODITIES TABLE INDEXES
    # ============================================================
    
    print("  - Commodity indexes...")
    
    # Index 7: Name search (case-insensitive)
    op.create_index(
        'ix_commodities_name_lower',
        'commodities',
        [sa.text('LOWER(name)')],
        unique=False
    )
    
    # Index 8: Category filtering
    op.create_index(
        'ix_commodities_category',
        'commodities',
        ['category'],
        unique=False
    )
    
    # Index 9: Active commodities only
    op.create_index(
        'ix_commodities_is_active',
        'commodities',
        ['is_active'],
        unique=False
    )
    
    # ============================================================
    # MANDIS TABLE INDEXES
    # ============================================================
    
    print("  - Mandi indexes...")
    
    # Index 10: State filtering
    op.create_index(
        'ix_mandis_state',
        'mandis',
        ['state'],
        unique=False
    )
    
    # Index 11: District filtering
    op.create_index(
        'ix_mandis_district',
        'mandis',
        ['district'],
        unique=False
    )
    
    # Index 12: State + District composite (most common filter)
    op.create_index(
        'ix_mandis_state_district',
        'mandis',
        ['state', 'district'],
        unique=False
    )
    
    # Index 13: Name search (case-insensitive)
    op.create_index(
        'ix_mandis_name_lower',
        'mandis',
        [sa.text('LOWER(name)')],
        unique=False
    )
    
    # Index 14: Active mandis only
    op.create_index(
        'ix_mandis_is_active',
        'mandis',
        ['is_active'],
        unique=False
    )
    
    # ============================================================
    # COMMUNITY_POSTS TABLE INDEXES
    # ============================================================
    
    print("  - Community posts indexes...")
    
    # Index 15: post_type + created_at (common query)
    op.create_index(
        'ix_community_posts_type_created',
        'community_posts',
        ['post_type', 'created_at'],
        unique=False
    )
    
    # Index 16: User lookup
    op.create_index(
        'ix_community_posts_user_id',
        'community_posts',
        ['user_id'],
        unique=False
    )
    
    # Index 17: Created date (for sorting)
    op.create_index(
        'ix_community_posts_created_at',
        'community_posts',
        ['created_at'],
        unique=False
    )
    
    # ============================================================
    # COMMUNITY_REPLIES TABLE INDEXES
    # ============================================================
    
    print("  - Community replies indexes...")
    
    # Index 18: Post lookup
    op.create_index(
        'ix_community_replies_post_id',
        'community_replies',
        ['post_id'],
        unique=False
    )
    
    # Index 19: User lookup
    op.create_index(
        'ix_community_replies_user_id',
        'community_replies',
        ['user_id'],
        unique=False
    )
    
    # Index 20: Post + created_at (for sorting replies)
    op.create_index(
        'ix_community_replies_post_created',
        'community_replies',
        ['post_id', 'created_at'],
        unique=False
    )
    
    # ============================================================
    # USERS TABLE INDEXES
    # ============================================================
    
    print("  - User indexes...")
    
    # Index 21: State filtering for user management
    op.create_index(
        'ix_users_state',
        'users',
        ['state'],
        unique=False
    )
    
    # Index 22: District filtering
    op.create_index(
        'ix_users_district',
        'users',
        ['district'],
        unique=False
    )
    
    # Index 23: Admin users filtering
    op.create_index(
        'ix_users_role',
        'users',
        ['role'],
        unique=False
    )
    
    # Index 24: Banned status
    op.create_index(
        'ix_users_is_banned',
        'users',
        ['is_banned'],
        unique=False
    )
    
    # ============================================================
    # INVENTORY TABLE INDEXES
    # ============================================================
    
    print("  - Inventory indexes...")
    
    # Index 25: User's inventory lookup
    op.create_index(
        'ix_inventory_user_id',
        'inventory',
        ['user_id'],
        unique=False
    )
    
    # Index 26: Commodity in inventory
    op.create_index(
        'ix_inventory_commodity_id',
        'inventory',
        ['commodity_id'],
        unique=False
    )
    
    # ============================================================
    # SALES TABLE INDEXES
    # ============================================================
    
    print("  - Sales indexes...")
    
    # Index 27: User's sales lookup
    op.create_index(
        'ix_sales_user_id',
        'sales',
        ['user_id'],
        unique=False
    )
    
    # Index 28: Sale date (for date range queries)
    op.create_index(
        'ix_sales_sale_date',
        'sales',
        ['sale_date'],
        unique=False
    )
    
    # Index 29: User + date composite
    op.create_index(
        'ix_sales_user_date',
        'sales',
        ['user_id', 'sale_date'],
        unique=False
    )
    
    # ============================================================
    # NOTIFICATIONS TABLE INDEXES
    # ============================================================
    
    print("  - Notification indexes...")
    
    # Index 30: User's notifications
    op.create_index(
        'ix_notifications_user_id',
        'notifications',
        ['user_id'],
        unique=False
    )
    
    # Index 31: Unread notifications
    op.create_index(
        'ix_notifications_is_read',
        'notifications',
        ['is_read'],
        unique=False
    )
    
    # Index 32: User + read status
    op.create_index(
        'ix_notifications_user_read',
        'notifications',
        ['user_id', 'is_read'],
        unique=False
    )
    
    print("✓ Created 32 performance indexes successfully")


def downgrade() -> None:
    """Remove performance indexes."""
    
    print("Removing performance indexes...")
    
    # Drop in reverse order
    
    # Notifications
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    
    # Sales
    op.drop_index('ix_sales_user_date', table_name='sales')
    op.drop_index('ix_sales_sale_date', table_name='sales')
    op.drop_index('ix_sales_user_id', table_name='sales')
    
    # Inventory
    op.drop_index('ix_inventory_commodity_id', table_name='inventory')
    op.drop_index('ix_inventory_user_id', table_name='inventory')
    
    # Users
    op.drop_index('ix_users_is_banned', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_district', table_name='users')
    op.drop_index('ix_users_state', table_name='users')
    
    # Community Replies
    op.drop_index('ix_community_replies_post_created', table_name='community_replies')
    op.drop_index('ix_community_replies_user_id', table_name='community_replies')
    op.drop_index('ix_community_replies_post_id', table_name='community_replies')
    
    # Community Posts
    op.drop_index('ix_community_posts_created_at', table_name='community_posts')
    op.drop_index('ix_community_posts_user_id', table_name='community_posts')
    op.drop_index('ix_community_posts_type_created', table_name='community_posts')
    
    # Mandis
    op.drop_index('ix_mandis_is_active', table_name='mandis')
    op.drop_index('ix_mandis_name_lower', table_name='mandis')
    op.drop_index('ix_mandis_state_district', table_name='mandis')
    op.drop_index('ix_mandis_district', table_name='mandis')
    op.drop_index('ix_mandis_state', table_name='mandis')
    
    # Commodities
    op.drop_index('ix_commodities_is_active', table_name='commodities')
    op.drop_index('ix_commodities_category', table_name='commodities')
    op.drop_index('ix_commodities_name_lower', table_name='commodities')
    
    # Price History
    op.drop_index('ix_price_history_commodity_mandi_date', table_name='price_history')
    op.drop_index('ix_price_history_mandi_date', table_name='price_history')
    op.drop_index('ix_price_history_commodity_date', table_name='price_history')
    op.drop_index('ix_price_history_price_date', table_name='price_history')
    op.drop_index('ix_price_history_mandi_id', table_name='price_history')
    op.drop_index('ix_price_history_commodity_id', table_name='price_history')
    
    print("✓ Removed all performance indexes")
