"""add_district_name_map

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-03-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "district_name_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_dataset", sa.String(20), nullable=False),
        sa.Column("state_name", sa.String(100), nullable=False),
        sa.Column("source_district", sa.String(200), nullable=False),
        sa.Column("canonical_district", sa.String(200), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_type", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_dataset",
            "state_name",
            "source_district",
            name="uq_district_name_map_source",
        ),
    )
    op.create_index(
        "idx_district_map_canonical",
        "district_name_map",
        ["state_name", "canonical_district"],
    )
    op.create_index(
        "idx_district_map_match_type",
        "district_name_map",
        ["match_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_district_map_match_type", table_name="district_name_map")
    op.drop_index("idx_district_map_canonical", table_name="district_name_map")
    op.drop_table("district_name_map")
