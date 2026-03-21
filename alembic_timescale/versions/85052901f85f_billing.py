"""billing

Revision ID: 85052901f85f
Revises: d41189591b31
Create Date: 2026-03-21 10:40:59.079696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '85052901f85f'
down_revision: Union[str, Sequence[str], None] = 'd41189591b31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(text("""ALTER MATERIALIZED VIEW "Billing".daily_billing_summary 
SET (timescaledb.materialized_only = false);
"""))


def downgrade() -> None:
    """Downgrade schema."""
    pass
