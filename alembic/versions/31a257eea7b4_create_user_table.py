"""Create user table

Revision ID: 31a257eea7b4
Revises:
Create Date: 2025-09-15 14:26:12.067927

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "31a257eea7b4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password CHAR(80) NOT NULL,
    created_at TIMESTAMP DEFAULT now() NOT NULL,
    updated_at TIMESTAMP DEFAULT now() NOT NULL
);
""".strip()
    )
    op.execute("""CREATE INDEX ix_users_email ON users (email);""")
    op.execute(
        """ALTER TABLE users
    ADD CONSTRAINT ck_user_email CHECK (char_length(email) > 5);"""
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("users")
    pass
