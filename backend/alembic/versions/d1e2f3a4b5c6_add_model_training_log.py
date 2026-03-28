"""add_model_training_log

Revision ID: d1e2f3a4b5c6
Revises: c2d3e4f5a6b7
Create Date: 2026-03-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_training_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity", sa.String(200), nullable=False),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("n_series", sa.Integer(), nullable=False),
        sa.Column("n_folds", sa.Integer(), nullable=False),
        sa.Column("rmse_fold_1", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_fold_2", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_fold_3", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_fold_4", sa.Numeric(10, 4), nullable=True),
        sa.Column("rmse_mean", sa.Numeric(10, 4), nullable=False),
        sa.Column("mape_mean", sa.Numeric(10, 4), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("skforecast_version", sa.String(20), nullable=False),
        sa.Column("xgboost_version", sa.String(20), nullable=False),
        sa.Column("excluded_districts", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_model_training_log_commodity",
        "model_training_log",
        ["commodity"],
    )


def downgrade() -> None:
    op.drop_index("idx_model_training_log_commodity", table_name="model_training_log")
    op.drop_table("model_training_log")
