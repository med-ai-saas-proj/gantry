"""add api key uuid

Revision ID: c5a9f1391d7e
Revises: 778951e24058
Create Date: 2026-05-03 16:30:00.000000
Feature:
Reason:

"""

from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c5a9f1391d7e"
down_revision: Union[str, Sequence[str], None] = "778951e24058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "ApiKeys",
        sa.Column("uuid", sa.Uuid(), nullable=True),
        schema="ApiKey",
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text('SELECT id FROM "ApiKey"."ApiKeys" WHERE uuid IS NULL')
    ).fetchall()
    for row in rows:
        bind.execute(
            sa.text(
                'UPDATE "ApiKey"."ApiKeys" SET uuid = :uuid WHERE id = :id'
            ),
            {"id": row.id, "uuid": str(uuid.uuid4())},
        )

    op.alter_column(
        "ApiKeys",
        "uuid",
        nullable=False,
        schema="ApiKey",
    )
    op.create_index(
        op.f("ApiKeys_uuid_idx"),
        "ApiKeys",
        ["uuid"],
        unique=True,
        schema="ApiKey",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ApiKeys_uuid_idx"),
        table_name="ApiKeys",
        schema="ApiKey",
    )
    op.drop_column("ApiKeys", "uuid", schema="ApiKey")
