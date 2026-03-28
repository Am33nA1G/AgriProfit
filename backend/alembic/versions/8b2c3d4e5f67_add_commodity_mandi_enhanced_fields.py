"""Add commodity and mandi enhanced fields

Revision ID: 8b2c3d4e5f67
Revises: 7ca1e1eba75a
Create Date: 2026-02-02 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8b2c3d4e5f67'
down_revision: Union[str, Sequence[str], None] = '3403efed2892'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add enhanced fields to commodities and mandis tables."""
    
    # === COMMODITIES TABLE ENHANCEMENTS ===
    
    # Description field
    op.add_column('commodities', sa.Column('description', sa.Text(), nullable=True))
    
    # Seasonal information
    op.add_column('commodities', sa.Column('growing_months', postgresql.ARRAY(sa.Integer()), nullable=True))
    op.add_column('commodities', sa.Column('harvest_months', postgresql.ARRAY(sa.Integer()), nullable=True))
    op.add_column('commodities', sa.Column('peak_season_start', sa.Integer(), nullable=True))
    op.add_column('commodities', sa.Column('peak_season_end', sa.Integer(), nullable=True))
    
    # Regional information
    op.add_column('commodities', sa.Column('major_producing_states', postgresql.ARRAY(sa.String(100)), nullable=True))
    
    # Status (if not exists)
    op.add_column('commodities', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    
    # === MANDIS TABLE ENHANCEMENTS ===
    
    # Pincode
    op.add_column('mandis', sa.Column('pincode', sa.String(length=10), nullable=True))
    
    # Contact information
    op.add_column('mandis', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('mandis', sa.Column('email', sa.String(length=100), nullable=True))
    op.add_column('mandis', sa.Column('website', sa.String(length=200), nullable=True))
    
    # Operating hours
    op.add_column('mandis', sa.Column('opening_time', sa.Time(), nullable=True))
    op.add_column('mandis', sa.Column('closing_time', sa.Time(), nullable=True))
    op.add_column('mandis', sa.Column('operating_days', postgresql.ARRAY(sa.String(20)), nullable=True))
    
    # Facilities
    op.add_column('mandis', sa.Column('has_weighbridge', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('mandis', sa.Column('has_storage', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('mandis', sa.Column('has_loading_dock', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('mandis', sa.Column('has_cold_storage', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    
    # Payment and commodities
    op.add_column('mandis', sa.Column('payment_methods', postgresql.ARRAY(sa.String(50)), nullable=True))
    op.add_column('mandis', sa.Column('commodities_accepted', postgresql.ARRAY(sa.String(100)), nullable=True))
    
    # Rating
    op.add_column('mandis', sa.Column('rating', sa.Float(), nullable=True))
    op.add_column('mandis', sa.Column('total_reviews', sa.Integer(), nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    """Remove enhanced fields from commodities and mandis tables."""
    
    # === MANDIS TABLE ===
    op.drop_column('mandis', 'total_reviews')
    op.drop_column('mandis', 'rating')
    op.drop_column('mandis', 'commodities_accepted')
    op.drop_column('mandis', 'payment_methods')
    op.drop_column('mandis', 'has_cold_storage')
    op.drop_column('mandis', 'has_loading_dock')
    op.drop_column('mandis', 'has_storage')
    op.drop_column('mandis', 'has_weighbridge')
    op.drop_column('mandis', 'operating_days')
    op.drop_column('mandis', 'closing_time')
    op.drop_column('mandis', 'opening_time')
    op.drop_column('mandis', 'website')
    op.drop_column('mandis', 'email')
    op.drop_column('mandis', 'phone')
    op.drop_column('mandis', 'pincode')
    
    # === COMMODITIES TABLE ===
    op.drop_column('commodities', 'is_active')
    op.drop_column('commodities', 'major_producing_states')
    op.drop_column('commodities', 'peak_season_end')
    op.drop_column('commodities', 'peak_season_start')
    op.drop_column('commodities', 'harvest_months')
    op.drop_column('commodities', 'growing_months')
    op.drop_column('commodities', 'description')
