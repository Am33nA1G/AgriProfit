"""Fix community post_type constraint

Revision ID: 54c3d229b845
Revises: 7a354a7a6bc4
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '54c3d229b845'
down_revision: Union[str, Sequence[str], None] = '7a354a7a6bc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix post_type constraint to match API schema."""
    # Drop the old constraint
    op.drop_constraint('community_posts_post_type_check', 'community_posts', type_='check')

    # Update existing data: map old values to new valid values
    op.execute("UPDATE community_posts SET post_type = 'discussion' WHERE post_type = 'normal'")
    op.execute("UPDATE community_posts SET post_type = 'announcement' WHERE post_type = 'alert'")

    # Add the new constraint matching the API schema
    op.create_check_constraint(
        'community_posts_post_type_check',
        'community_posts',
        "post_type IN ('discussion', 'question', 'tip', 'announcement')"
    )


def downgrade() -> None:
    """Revert to old post_type constraint."""
    # Drop the new constraint
    op.drop_constraint('community_posts_post_type_check', 'community_posts', type_='check')

    # Revert data: map new values back to old values
    op.execute("UPDATE community_posts SET post_type = 'normal' WHERE post_type IN ('discussion', 'question', 'tip')")
    op.execute("UPDATE community_posts SET post_type = 'alert' WHERE post_type = 'announcement'")

    # Restore old constraint
    op.create_check_constraint(
        'community_posts_post_type_check',
        'community_posts',
        "post_type IN ('normal', 'alert')"
    )
