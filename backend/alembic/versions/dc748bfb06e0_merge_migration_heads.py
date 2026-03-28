"""merge migration heads

Revision ID: dc748bfb06e0
Revises: a3b4c5d6e7f8, e1f2a3b4c5d6
Create Date: 2026-03-10 06:08:52.160508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc748bfb06e0'
down_revision: Union[str, Sequence[str], None] = ('a3b4c5d6e7f8', 'e1f2a3b4c5d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
