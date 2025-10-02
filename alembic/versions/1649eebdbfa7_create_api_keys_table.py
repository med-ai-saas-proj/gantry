"""create_api_keys_table

Revision ID: 1649eebdbfa7
Revises: 310ab3cafdbf
Create Date: 2025-09-16 17:59:54.801410

"""

from alembic import op

from typing import Union, Sequence

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1649eebdbfa7"
down_revision: Union[str, Sequence[str], None] = "310ab3cafdbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            sa.types.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.types.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "api_key",
            sa.types.String(255),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.types.String(255),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.types.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.types.TIMESTAMP(),
            nullable=True,
        ),
        sa.Column(
            "expires_at",
            sa.types.TIMESTAMP(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.types.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.types.TIMESTAMP(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index on user_id for better query performance
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # Create index on api_key for faster lookups
    op.create_index("ix_api_keys_api_key", "api_keys", ["api_key"])

    # Create index on is_active for filtering active keys
    op.create_index("ix_api_keys_is_active", "api_keys", ["is_active"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_api_keys_is_active", "api_keys")
    op.drop_index("ix_api_keys_api_key", "api_keys")
    op.drop_index("ix_api_keys_user_id", "api_keys")
    op.drop_table("api_keys")
