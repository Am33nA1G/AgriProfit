"""add_user_ban_fields

Revision ID: d0bc3dcef208
Revises: 701f160917f6
Create Date: 2026-02-05 16:13:21.008856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0bc3dcef208'
down_revision: Union[str, Sequence[str], None] = '701f160917f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False))
    op.add_column('users', sa.Column('ban_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'ban_reason')
    op.drop_column('users', 'is_banned')
