"""add_price_bounds

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_bounds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity", sa.String(200), nullable=False),
        sa.Column("commodity_id", sa.Integer(), nullable=True),
        sa.Column("q1", sa.Numeric(12, 2), nullable=True),
        sa.Column("q3", sa.Numeric(12, 2), nullable=True),
        sa.Column("iqr", sa.Numeric(12, 2), nullable=True),
        sa.Column("lower_cap", sa.Numeric(12, 2), nullable=True),
        sa.Column("upper_cap", sa.Numeric(12, 2), nullable=True),
        sa.Column("median_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("outlier_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("commodity", name="uq_price_bounds_commodity"),
    )


def downgrade() -> None:
    op.drop_table("price_bounds")
