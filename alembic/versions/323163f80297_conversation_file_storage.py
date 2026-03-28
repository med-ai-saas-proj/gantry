"""conversation_file_storage

Revision ID: 323163f80297
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 16:56:51.398912
Feature:
Reason:

"""

from alembic import op

from typing import Union, Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "323163f80297"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
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
    path = script_directory / "323163f80297_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "323163f80297_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
