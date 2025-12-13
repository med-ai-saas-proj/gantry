"""Api keys and Permissions

Revision ID: 909c37558b63
Revises:
Create Date: 2025-12-13 14:49:23.811335
Feature:
Reason:

"""

from alembic import op

from typing import Union, Sequence
from pathlib import Path

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "909c37558b63"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

script_path = Path(__file__).resolve()
script_directory = script_path.parent


def executeScript(script: str):
    statements = script.split(";")
    for statement in statements:
        stmt = statement.strip()
        if stmt not in ["BEGIN", "END", "COMMIT"]:
            op.execute(stmt + ";")


def upgrade() -> None:
    """Upgrade schema."""
    path = script_directory / "909c37558b63_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "909c37558b63_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass
