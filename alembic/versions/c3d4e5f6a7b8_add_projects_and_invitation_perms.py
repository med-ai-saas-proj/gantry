"""add_projects_table_and_invitation_permissions

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26 22:50:00.000000
Feature: Organization
Reason: Add Projects table and permissions column to Invitations

"""
from alembic import op

from typing import Sequence, Union
from pathlib import Path

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
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
    path = script_directory / "c3d4e5f6a7b8_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "c3d4e5f6a7b8_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass
