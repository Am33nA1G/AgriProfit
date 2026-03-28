"""add_forecast_accuracy_log

Revision ID: a3b4c5d6e7f8
Revises: f1a2b3c4d5e6
Create Date: 2026-03-10 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "forecast_accuracy_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("commodity_name", sa.String(200), nullable=False),
        sa.Column("district_name", sa.String(200), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("predicted_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("absolute_pct_error", sa.Float(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_forecast_accuracy_lookup",
        "forecast_accuracy_log",
        ["commodity_name", "district_name", "target_date", "model_version"],
    )


def downgrade() -> None:
    op.drop_index("idx_forecast_accuracy_lookup", table_name="forecast_accuracy_log")
    op.drop_table("forecast_accuracy_log")
