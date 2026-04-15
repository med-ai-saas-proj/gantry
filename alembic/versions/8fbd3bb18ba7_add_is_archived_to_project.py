"""add is_archived to project

Revision ID: 8fbd3bb18ba7
Revises: e12c66752b92
Create Date: 2026-04-15 16:01:34.058333
Feature:
Reason:

"""

from alembic import op

from typing import Union, Sequence
from pathlib import Path

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8fbd3bb18ba7"
down_revision: Union[str, Sequence[str], None] = "e12c66752b92"
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
    path = script_directory / "8fbd3bb18ba7_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "8fbd3bb18ba7_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass
