"""merge heads

Revision ID: 4be60c2d7319
Revises: a1b2c3d4e5f6, d3e4f5a6b7c8
Create Date: 2026-03-02 23:54:58.864613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4be60c2d7319'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'd3e4f5a6b7c8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
