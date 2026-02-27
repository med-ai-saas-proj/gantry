"""add_org_metadata_table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-27 01:20:00.000000
Feature: Organization
Reason: Persist org owner and metadata for invariants and auditing

"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

script_path = Path(__file__).resolve()
script_directory = script_path.parent


def executeScript(script: str):
    statements = script.split(";")
    for statement in statements:
        stmt = statement.strip()
        if stmt not in ["BEGIN", "END", "COMMIT"] and stmt:
            op.execute(stmt + ";")


def upgrade() -> None:
    """Upgrade schema."""
    path = script_directory / "d4e5f6a7b8c9_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "d4e5f6a7b8c9_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
