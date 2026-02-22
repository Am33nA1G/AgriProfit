"""add_device_push_tokens

Revision ID: a2b3c4d5e6f7
Revises: f9e8d7c6b5a4
Create Date: 2026-02-21 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_push_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expo_push_token", sa.String(255), nullable=False),
        sa.Column("device_platform", sa.String(10), nullable=False),
        sa.Column("device_model", sa.String(100), nullable=True),
        sa.Column("app_version", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP, server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("user_id", "expo_push_token", name="uq_user_push_token"),
        sa.CheckConstraint(
            "device_platform IN ('ios', 'android')",
            name="ck_device_platform",
        ),
    )

    op.create_index(
        "idx_push_tokens_user_active",
        "device_push_tokens",
        ["user_id", "is_active"],
    )
    op.create_index(
        "idx_push_tokens_token",
        "device_push_tokens",
        ["expo_push_token"],
    )


def downgrade() -> None:
    op.drop_index("idx_push_tokens_token", table_name="device_push_tokens")
    op.drop_index("idx_push_tokens_user_active", table_name="device_push_tokens")
    op.drop_table("device_push_tokens")
