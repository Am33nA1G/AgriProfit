"""add_road_distance_cache

Revision ID: a2b3c4d5e6f7
Revises: f9e8d7c6b5a4
Create Date: 2026-02-28 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "road_distance_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("origin_key", sa.String(32), nullable=False),
        sa.Column("destination_key", sa.String(32), nullable=False),
        sa.Column("src_lat", sa.Float(), nullable=False),
        sa.Column("src_lon", sa.Float(), nullable=False),
        sa.Column("dst_lat", sa.Float(), nullable=False),
        sa.Column("dst_lon", sa.Float(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("origin_key", "destination_key", name="uq_road_distance_route"),
    )


def downgrade() -> None:
    op.drop_table("road_distance_cache")
