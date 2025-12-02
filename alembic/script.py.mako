"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
Feature: 
Reason: 

"""
from alembic import op

from typing import Sequence, Union
from pathlib import Path

import sqlalchemy as sa

${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}

script_path = Path(__file__).resolve()
script_directory = script_path.parent

def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "You are done"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "You are done"}
