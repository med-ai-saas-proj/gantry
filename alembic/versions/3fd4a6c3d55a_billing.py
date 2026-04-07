"""billing

Revision ID: 3fd4a6c3d55a
Revises: b7c8d9e0f1a2
Create Date: 2026-04-07 15:11:05.869107
Feature:
Reason:

"""

from alembic import op

from typing import Union, Sequence
from pathlib import Path

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3fd4a6c3d55a"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
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
    path = script_directory / "3fd4a6c3d55a_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "3fd4a6c3d55a_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass
