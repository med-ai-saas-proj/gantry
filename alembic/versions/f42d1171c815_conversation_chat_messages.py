"""Conversation & chat messages

Revision ID: f42d1171c815
Revises: 1649eebdbfa7
Create Date: 2025-10-13 10:32:40.897513
Feature:
Reason:

"""

from alembic import op

from typing import Union, Sequence
from pathlib import Path

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f42d1171c815"
down_revision: Union[str, Sequence[str], None] = "1649eebdbfa7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

script_path = Path(__file__).resolve()
script_directory = script_path.parent


def upgrade() -> None:
    """Upgrade schema."""
    with open(script_directory / "f42d1171c815_upgrade.sql") as f:
        sql = f.read()
    op.execute(sql)
    pass


def downgrade() -> None:
    """Downgrade schema."""
    with open(script_directory / "f42d1171c815_downgrade.sql") as f:
        sql = f.read()
    op.execute(sql)
    pass
