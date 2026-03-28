"""add_soil_advisor_tables

Revision ID: e1f2a3b4c5d6
Revises: 4be60c2d7319, e2f3a4b5c6d7
Create Date: 2026-03-03 01:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = ("4be60c2d7319", "e2f3a4b5c6d7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "soil_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("district", sa.String(200), nullable=False),
        sa.Column("block", sa.String(300), nullable=False),
        sa.Column("cycle", sa.String(10), nullable=False),
        sa.Column("nutrient", sa.String(50), nullable=False),
        sa.Column("high_pct", sa.SmallInteger(), nullable=False),
        sa.Column("medium_pct", sa.SmallInteger(), nullable=False),
        sa.Column("low_pct", sa.SmallInteger(), nullable=False),
        sa.Column(
            "seeded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("state", "district", "block", "cycle", "nutrient", name="uq_soil_profile"),
    )

    op.create_table(
        "soil_crop_suitability",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("crop_name", sa.String(200), nullable=False),
        sa.Column("nutrient", sa.String(50), nullable=False),
        sa.Column("min_tolerance", sa.String(10), nullable=False),
        sa.Column("ph_min", sa.Numeric(4, 1), nullable=True),
        sa.Column("ph_max", sa.Numeric(4, 1), nullable=True),
        sa.Column("fertiliser_advice", sa.Text(), nullable=False),
        sa.UniqueConstraint("crop_name", "nutrient", name="uq_crop_nutrient"),
    )

    op.create_index("idx_soil_profile_location", "soil_profiles", ["state", "district", "block"])
    op.create_index("idx_soil_profile_state", "soil_profiles", ["state"])
    op.create_index("idx_soil_profile_cycle", "soil_profiles", ["cycle"])


def downgrade() -> None:
    op.drop_index("idx_soil_profile_cycle", "soil_profiles")
    op.drop_index("idx_soil_profile_state", "soil_profiles")
    op.drop_index("idx_soil_profile_location", "soil_profiles")
    op.drop_table("soil_crop_suitability")
    op.drop_table("soil_profiles")
