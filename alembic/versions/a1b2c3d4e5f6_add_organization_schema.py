"""add_organization_schema

Revision ID: a1b2c3d4e5f6
Revises: 0433e52b355a
Create Date: 2026-02-12 00:09:00.000000
Feature: Organization
Reason: Add Organization schema with Settings and DeletionRequests tables

"""
from alembic import op

from typing import Sequence, Union
from pathlib import Path

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0433e52b355a'
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
    path = script_directory / "a1b2c3d4e5f6_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "a1b2c3d4e5f6_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
    else:
        open(path, "w")
        pass
