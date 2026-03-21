"""billing

Revision ID: d41189591b31
Revises: ddada74c8edf
Create Date: 2026-03-21 09:05:27.148843

"""
from alembic import op

from typing import Union, Sequence


# revision identifiers, used by Alembic.
revision: str = 'd41189591b31'
down_revision: Union[str, Sequence[str], None] = 'ddada74c8edf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
    DROP MATERIALIZED VIEW IF EXISTS "Billing".daily_billing_summary;
    """)

    op.execute(
        """
        CREATE MATERIALIZED VIEW "Billing".daily_billing_summary
    WITH (timescaledb.continuous) AS
    SELECT 
        time_bucket('1 day', created_at) AS bucket,
        apikey_id,
        project_id,
        organization_id,
        SUM(amount) AS total_amount,
        COUNT(*) AS transaction_count
    FROM "Billing"."BillingTransactions"
    GROUP BY bucket, apikey_id, project_id, organization_id
    with no data;
        """
    )
    op.execute("""
    SELECT add_continuous_aggregate_policy('"Billing".daily_billing_summary',
        start_offset => INTERVAL '3 days',
        end_offset => INTERVAL '0 seconds',
        schedule_interval => INTERVAL '1 hour');
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
    DROP MATERIALIZED VIEW IF EXISTS "Billing".daily_billing_summary;
    """)
