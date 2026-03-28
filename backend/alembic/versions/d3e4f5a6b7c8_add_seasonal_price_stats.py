"""add_seasonal_price_stats

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-03-02 23:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seasonal_price_stats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity_name", sa.String(200), nullable=False),
        sa.Column("state_name", sa.String(100), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("median_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("q1_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("q3_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("iqr_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("years_of_data", sa.SmallInteger(), nullable=False),
        sa.Column("is_best", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_worst", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("month_rank", sa.SmallInteger(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "commodity_name", "state_name", "month",
            name="uq_seasonal_commodity_state_month",
        ),
    )
    op.create_index(
        "idx_seasonal_commodity_state",
        "seasonal_price_stats",
        ["commodity_name", "state_name"],
    )


def downgrade() -> None:
    op.drop_index("idx_seasonal_commodity_state", table_name="seasonal_price_stats")
    op.drop_table("seasonal_price_stats")
