"""Add community alert features

Add image_url, view_count, is_pinned columns to community_posts.
Add 'alert' to post_type constraint for distinct alert behavior.

Revision ID: a1b2c3d4e5f6
Revises: f9e8d7c6b5a4
Create Date: 2026-02-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f9e8d7c6b5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add alert features to community_posts."""
    # Add new columns
    op.add_column('community_posts', sa.Column('image_url', sa.Text(), nullable=True))
    op.add_column('community_posts', sa.Column('view_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('community_posts', sa.Column('is_pinned', sa.Boolean(), server_default='false', nullable=False))

    # Update post_type constraint to include 'alert'
    op.drop_constraint('community_posts_post_type_check', 'community_posts', type_='check')
    op.create_check_constraint(
        'community_posts_post_type_check',
        'community_posts',
        "post_type IN ('discussion', 'question', 'tip', 'announcement', 'alert')"
    )

    # Add index for pinned + alert ordering
    op.create_index(
        'idx_posts_pinned_alert',
        'community_posts',
        [sa.text('is_pinned DESC'), sa.text('created_at DESC')],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Remove alert features."""
    op.drop_index('idx_posts_pinned_alert', 'community_posts')

    # Revert post_type constraint
    op.execute("UPDATE community_posts SET post_type = 'announcement' WHERE post_type = 'alert'")
    op.drop_constraint('community_posts_post_type_check', 'community_posts', type_='check')
    op.create_check_constraint(
        'community_posts_post_type_check',
        'community_posts',
        "post_type IN ('discussion', 'question', 'tip', 'announcement')"
    )

    op.drop_column('community_posts', 'is_pinned')
    op.drop_column('community_posts', 'view_count')
    op.drop_column('community_posts', 'image_url')
