"""Add last_login to users

Revision ID: 367708e34977
Revises: 154188b9a722
Create Date: 2026-01-26 07:07:22.554466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '367708e34977'
down_revision: Union[str, Sequence[str], None] = '154188b9a722'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only adding last_login column to test migration workflow
    op.add_column('users', sa.Column('last_login', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_login')
