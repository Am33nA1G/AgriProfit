"""add_forecast_cache

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-03 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "forecast_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity_name", sa.String(200), nullable=False),
        sa.Column("district_name", sa.String(200), nullable=False),
        sa.Column("generated_date", sa.Date(), nullable=False),
        sa.Column("forecast_horizon_days", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("price_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_mid", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_high", sa.Numeric(10, 2), nullable=True),
        sa.Column("confidence_colour", sa.String(10), nullable=False),
        sa.Column("tier_label", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_forecast_cache_lookup",
        "forecast_cache",
        ["commodity_name", "district_name", "generated_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_forecast_cache_lookup", table_name="forecast_cache")
    op.drop_table("forecast_cache")
