"""Core billing service — HOLD/RELEASE pattern.

Flow (see architecture diagram):

  HOLD (called by Service#1 before processing the request):
    1. Fetch project limit + org limit + current org total in one DB transaction.
       - Project limit: ProjectSpendingLimit for this project (or None = unlimited).
       - Org limit:     OrganizationSpendingLimit for this org (or None = unlimited).
       - Org total:     SUM(total_amount) across all open aggregates for all org
                        projects this period. Provided by the caller as
                        BillingPing.org_project_ids — the org→project mapping lives
                        in Keycloak, not here.
    2. Pre-check org limit in code.
    3. Atomically upsert MonthlyAggregate via INSERT ON CONFLICT DO UPDATE WHERE
       — enforces the project-level limit inside Postgres. Concurrent HOLDs are
       serialised here so no two requests can both pass against the same stale total.
    4. Commit the Postgres row (durable — money is tracked even if Redis dies).
    5. Store hold metadata in Redis with TTL.
    6. Return hold UUID to the caller.
    → 403 SpendingLimitExceeded (project limit OR org limit breached).
    → 409 AggregateFinalized if the current period is already closed.

  RELEASE (called by Service#1 after computing the real cost):
    1. Fetch hold record from Redis by UUID.
       ↳ If Redis miss (crash / TTL expired): Err(HoldNotFound).
         The hold amount is still in Postgres — a reconciliation job (future
         ticket) can detect orphaned holds by comparing MonthlyAggregate
         totals against committed BillingTransactions.
    2. Compute delta = real_cost − hold_amount (usually ≤ 0).
    3. Adjust MonthlyAggregate in Postgres: total_amount += delta.
       ↳ If period was finalized between HOLD and RELEASE: Err(AggregateFinalized).
    4. Delete hold record from Redis only after Postgres commits.
    TODO(BILL-008): INSERT BillingTransaction into TimescaleDB.
"""

import asyncio

from src.db.factories import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError

from .dtos import BillingPing, ScaledAmount
from .repositories import (
    MonthlyAggregateRepository,
    SpendingLimitRepository,
)

import json
from uuid import UUID, uuid4
from typing import TypedDict
from decimal import Decimal
from datetime import datetime, timezone

from safe_result import Ok, Err, Result
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class SpendingLimitExceeded(RecoverableError):
    status = 403
    code = "spending_limit_exceeded"
    title = "Spending Limit Exceeded"
    detail = "The request would exceed the configured spending limit."


class HoldNotFound(RecoverableError):
    status = 404
    code = "hold_not_found"
    title = "Hold Not Found"
    detail = "The billing hold UUID does not exist or has expired."


# ---------------------------------------------------------------------------
# Redis configs
# ---------------------------------------------------------------------------


class _HoldRecord(TypedDict):
    project_id: int
    org_id: str
    apikey_id: int
    hold_amount: ScaledAmount
    billing_period: str  # "YYYY-MM" — period active when HOLD was placed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_billing_period() -> str:
    """Return the current UTC billing period in YYYY-MM format."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _to_decimal(amount: ScaledAmount) -> Decimal:
    """Convert a ScaledAmount to a Python Decimal.

    Decimal.scaleb(n) multiplies by 10^n — exact integer arithmetic, no float.
    """
    return Decimal(amount["value"]).scaleb(-amount["scale"])


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BillingService:
    """Implements the two-phase HOLD / RELEASE billing protocol."""

    _HOLD_KEY = "billing:hold:{uuid}"
    _HOLD_TTL = 3600  # seconds

    def __init__(
        self,
        logger: BoundLogger,
        session_manager: AsyncSessionManager,
        redis: Redis,
        monthly_agg_repo: MonthlyAggregateRepository,
        spending_limit_repo: SpendingLimitRepository,
    ) -> None:
        self.logger = logger
        self.session_manager = session_manager
        self.redis = redis
        self.monthly_agg_repo = monthly_agg_repo
        self.spending_limit_repo = spending_limit_repo

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def hold(
        self, ping: BillingPing
    ) -> Result[UUID, SpendingLimitExceeded]:
        """Reserve spending capacity before a request is processed.

        Returns Ok(hold_uuid) on success.
        """
        org_id = ping["organization_id"]
        project_id = ping["project_id"]
        billing_period = _current_billing_period()
        hold_amount = _to_decimal(ping["amount"])

        async with self.session_manager.get_session() as session:
            proj_limit_row, org_limit_row = await asyncio.gather(
                self.spending_limit_repo.getForProject(
                    session, project_id
                ),
                self.spending_limit_repo.getForOrg(session, org_id)
            )
            project_limit: Decimal | None = (
                proj_limit_row.monthly_limit
                if proj_limit_row is not None
                else None
            )
            org_limit: Decimal | None = (
                org_limit_row.monthly_limit
                if org_limit_row is not None
                else None
            )

            # Returns None if project_limit would be exceeded OR period finalized.
            agg = await self.monthly_agg_repo.holdAggregate(
                session, 
                project_id, 
                org_id,
                billing_period, 
                hold_amount, 
                project_limit,
                org_limit,
            )

            if agg is None:
                return Err(SpendingLimitExceeded())

            # Commit to Postgres before touching Redis — if Redis write fails
            await session.commit()

        hold_uuid = uuid4()
        hold_record: _HoldRecord = {
            "project_id": project_id,
            "org_id": org_id,
            "apikey_id": ping["apikey_id"],
            "hold_amount": ping["amount"],
            "billing_period": billing_period,
        }
        hold_key = self._HOLD_KEY.format(uuid=hold_uuid)
        await self.redis.set(
            hold_key, json.dumps(hold_record), ex=self._HOLD_TTL
        )

        self.logger.info(
            "billing.hold.ok",
            hold_uuid=str(hold_uuid),
            project_id=project_id,
            billing_period=billing_period,
        )
        return Ok(hold_uuid)

    async def release(
        self,
        hold_uuid: UUID,
        real_amount: ScaledAmount,
    ) -> Result[bool, HoldNotFound]:
        """Commit the actual charge after a request completes.

        Returns Ok(True) on success.
        """
        hold_key = self._HOLD_KEY.format(uuid=hold_uuid)
        raw = await self.redis.get(hold_key)
        if raw is None:
            # Redis miss: TTL expired or Redis crashed.
            # The hold amount is still in the Postgres aggregate — a future reconciliation job should scan for holds whose TTL has passed and correct the aggregate.
            self.logger.error(
                "billing.release.hold_not_found",
                hold_uuid=str(hold_uuid),
            )
            return Err(HoldNotFound())

        hold: _HoldRecord = json.loads(raw)
        project_id: int = hold["project_id"]
        billing_period: str = hold["billing_period"]
        org_id: str = hold["org_id"]

        hold_amount = _to_decimal(hold["hold_amount"])
        real = _to_decimal(real_amount)
        # delta ≤ 0 in the typical case (hold over-estimated real cost)
        delta = real - hold_amount

        async with self.session_manager.get_session() as session:
            agg = await self.monthly_agg_repo.releaseAggregate(
                session, project_id, org_id, billing_period, delta
            )
            if agg is None:
                # Finalized period — should never happen in normal flow.
                self.logger.error(
                    "billing.release.finalized_aggregate",
                    hold_uuid=str(hold_uuid),
                    project_id=project_id,
                    billing_period=billing_period,
                    org_id=org_id
                )
                return Err(AggregateFinalized())

            # TODO(BILL-008): INSERT BillingTransaction into TimescaleDB.
            await session.commit()

        # Delete the hold from Redis only after Postgres commit succeeds.
        await self.redis.delete(hold_key)

        self.logger.info(
            "billing.release.ok",
            hold_uuid=str(hold_uuid),
            project_id=project_id,
            billing_period=billing_period,
            delta=str(delta),
        )
        return Ok(True)
