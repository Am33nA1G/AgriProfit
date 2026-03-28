"""add_harvest_advisor_tables

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-03-04 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # crop_yields
    op.create_table(
        "crop_yields",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("district", sa.String(200), nullable=False),
        sa.Column("crop_name", sa.String(200), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("area_ha", sa.Numeric(12, 2), nullable=True),
        sa.Column("production_t", sa.Numeric(12, 2), nullable=True),
        sa.Column("yield_kg_ha", sa.Numeric(10, 2), nullable=False),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="ICRISAT"),
    )
    op.create_index(
        "idx_crop_yields_district_crop_year",
        "crop_yields",
        ["district", "crop_name", "year"],
        unique=True,
    )

    # yield_model_log
    op.create_table(
        "yield_model_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("crop_category", sa.String(50), nullable=False),
        sa.Column("n_samples", sa.Integer(), nullable=False),
        sa.Column("n_crops", sa.Integer(), nullable=False),
        sa.Column("cv_r2_mean", sa.Numeric(6, 4), nullable=False),
        sa.Column("cv_rmse_mean", sa.Numeric(10, 2), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("sklearn_version", sa.String(20), nullable=True),
    )

    # open_meteo_cache
    op.create_table(
        "open_meteo_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("district", sa.String(200), nullable=False),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_json", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_open_meteo_cache_district_state",
        "open_meteo_cache",
        ["district", "state"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_open_meteo_cache_district_state", table_name="open_meteo_cache")
    op.drop_table("open_meteo_cache")
    op.drop_table("yield_model_log")
    op.drop_index("idx_crop_yields_district_crop_year", table_name="crop_yields")
    op.drop_table("crop_yields")
