"""fix_updated_at_default_value

Revision ID: 310ab3cafdbf
Revises: 31a257eea7b4
Create Date: 2025-09-16 14:20:13.847672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '310ab3cafdbf'
down_revision: Union[str, Sequence[str], None] = '31a257eea7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix the updated_at column to have a proper server default
    op.alter_column('users', 'updated_at', 
                   server_default=sa.func.now(),
                   existing_type=sa.types.TIMESTAMP(),
                   existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the server default from updated_at column
    op.alter_column('users', 'updated_at', 
                   server_default=None,
                   existing_type=sa.types.TIMESTAMP(),
                   existing_nullable=False)
