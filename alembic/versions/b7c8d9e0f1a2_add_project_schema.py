"""add_project_schema

Revision ID: b7c8d9e0f1a2
Revises: 323163f80297
Create Date: 2026-03-08 12:00:00.000000
Feature: Project
Reason: Add Project schema and convert Organization.Settings.extra to JSONB

"""

from alembic import op

from typing import Union, Sequence
from pathlib import Path


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "323163f80297"
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
    path = script_directory / "b7c8d9e0f1a2_upgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)


def downgrade() -> None:
    """Downgrade schema."""
    path = script_directory / "b7c8d9e0f1a2_downgrade.sql"
    if path.exists():
        with open(path) as f:
            sql = f.read()
        executeScript(sql)
