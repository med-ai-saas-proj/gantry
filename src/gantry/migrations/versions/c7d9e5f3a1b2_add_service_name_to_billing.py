"""add service_name to billing transactions and daily_billing_summary

Revision ID: c7d9e5f3a1b2
Revises: b9a6c6eab6dc
Create Date: 2026-07-25 17:25:00.000000
Feature:
Reason:

"""

from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c7d9e5f3a1b2"
down_revision: Union[str, Sequence[str], None] = "b9a6c6eab6dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add service_name column to BillingTransactions
    op.add_column(
        "BillingTransactions",
        sa.Column(
            "service_name",
            sa.String(length=128),
            nullable=False,
            server_default="unknown",
        ),
        schema="Billing",
    )
    op.create_index(
        op.f("BillingTransactions_service_name_idx"),
        "BillingTransactions",
        ["service_name"],
        unique=False,
        schema="Billing",
    )

    # Remove continuous aggregate policy before dropping the view
    op.execute(
        "SELECT remove_continuous_aggregate_policy('\"Billing\".daily_billing_summary');"
    )

    # Drop the old materialized view
    op.execute(
        'DROP MATERIALIZED VIEW IF EXISTS "Billing".daily_billing_summary'
    )

    # Recreate with service_name in SELECT and GROUP BY
    op.execute(
        """CREATE MATERIALIZED VIEW "Billing".daily_billing_summary
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket ('1 day', created_at) AS bucket,
            apikey_id,
            project_id,
            organization_id,
            service_name,
            SUM(amount) FILTER (
                WHERE
                    status IN ('CAPTURED', 'PENDING')
            ) AS total_amount,
            COUNT(*) AS transaction_count
        FROM "Billing"."BillingTransactions"
        GROUP BY
            bucket,
            apikey_id,
            project_id,
            organization_id,
            service_name
        WITH
            NO DATA;"""
    )

    op.execute(
        """ALTER MATERIALIZED VIEW "Billing".daily_billing_summary
        SET (
            timescaledb.materialized_only = false
        );"""
    )

    op.execute(
        """SELECT add_continuous_aggregate_policy (
        '"Billing".daily_billing_summary',
        start_offset => INTERVAL '3 days',
        end_offset => INTERVAL '0 seconds',
        schedule_interval => INTERVAL '1 hour'
    );"""
    )

    # Update compression segmentby to include service_name
    op.execute(
        """ALTER TABLE "Billing"."BillingTransactions" SET (
        timescaledb.compress_segmentby = 'apikey_id, project_id, organization_id, service_name'
    );"""
    )

    # op.execute(
    #     """CALL "public".refresh_continuous_aggregate (
    #         '"Billing"."daily_billing_summary"',
    #         '2020-01-01',
    #         (now() - INTERVAL '1 hour')::timestamp
    #     );"""
    # )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove policy and drop materialized view
    op.execute(
        "SELECT remove_continuous_aggregate_policy('\"Billing\".daily_billing_summary');"
    )

    op.execute(
        'DROP MATERIALIZED VIEW IF EXISTS "Billing".daily_billing_summary'
    )

    # Recreate view without service_name
    op.execute(
        """CREATE MATERIALIZED VIEW "Billing".daily_billing_summary
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket ('1 day', created_at) AS bucket,
            apikey_id,
            project_id,
            organization_id,
            SUM(amount) FILTER (
                WHERE
                    status IN ('CAPTURED', 'PENDING')
            ) AS total_amount,
            COUNT(*) AS transaction_count
        FROM "Billing"."BillingTransactions"
        GROUP BY
            bucket,
            apikey_id,
            project_id,
            organization_id
        WITH
            NO DATA;"""
    )

    op.execute(
        """ALTER MATERIALIZED VIEW "Billing".daily_billing_summary
        SET (
            timescaledb.materialized_only = false
        );"""
    )

    op.execute(
        """SELECT add_continuous_aggregate_policy (
        '"Billing".daily_billing_summary',
        start_offset => INTERVAL '3 days',
        end_offset => INTERVAL '0 seconds',
        schedule_interval => INTERVAL '1 hour'
    );"""
    )

    # Revert compression segmentby to original
    op.execute(
        """ALTER TABLE "Billing"."BillingTransactions" SET (
        timescaledb.compress_segmentby = 'apikey_id, project_id, organization_id'
    );"""
    )

    op.drop_index(
        op.f("BillingTransactions_service_name_idx"),
        table_name="BillingTransactions",
        schema="Billing",
    )

    op.drop_column(
        "BillingTransactions",
        "service_name",
        schema="Billing",
    )
