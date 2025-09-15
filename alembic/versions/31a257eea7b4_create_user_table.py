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
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.types.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.types.String(255),
            index=True,
            unique=True,
            nullable=False,
        ),
        sa.Column("password", sa.types.LargeBinary(256), nullable=False),
        sa.Column(
            "created_at",
            sa.types.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.types.TIMESTAMP(),
            insert_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_email", "users", sa.func.char_length(sa.column("email")) > 5
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("users")
    pass
