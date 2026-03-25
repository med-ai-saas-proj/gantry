from src.db.factories import AsyncSessionManager
from src.management.billing.dtos import PostRequest, ScaledAmount
from src.management.billing.models import SpendingLimitType
from src.management.api_keys.services import ApiKeyService
from src.shared.custom_types.error_exception import RecoverableError
from src.management.billing.repositories.spending_limit_repo import (
    SpendingLimitRepository,
)
from src.management.billing.repositories.billing_transaction_repo import (
    BillingTransactionRepository,
)

import json
from uuid import UUID, uuid4
from typing import TypedDict
from decimal import Decimal
from datetime import datetime, timezone

from safe_result import Ok, Err, Result
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger


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


class _HoldRecord(TypedDict):
    project_id: int
    org_id: str
    apikey_id: int
    hold_amount: ScaledAmount
    billing_period: str  # "YYYY-MM" — period active when HOLD was placed


def _current_billing_period() -> str:
    """Return the current UTC billing period in YYYY-MM format."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _to_decimal(amount: ScaledAmount) -> Decimal:
    """Convert a ScaledAmount to a Python Decimal.

    Decimal.scaleb(n) multiplies by 10^n — exact integer arithmetic, no float.
    """
    return Decimal(amount["value"]).scaleb(-amount["scale"])


class ProjectNotFound(RecoverableError):
    status = 404
    code = "project_not_found"
    title = "Project Not Found"
    detail = "One or more project UUIDs were not found in the organization."

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class BillingTransactionService:
    """Implements the two-phase HOLD / RELEASE billing protocol."""

    _HOLD_KEY = "billing:hold:{uuid}"
    _HOLD_TTL = 3600  # seconds

    def __init__(
        self,
        logger: BoundLogger,
        session_manager: AsyncSessionManager,
        redis: Redis,
        spending_limit_repo: SpendingLimitRepository,
        billing_transaction_repo: BillingTransactionRepository,
        apikey_service: ApiKeyService,
    ) -> None:
        self.logger = logger
        self.session_manager = session_manager
        self.redis = redis
        self.spending_limit_repo = spending_limit_repo
        self.billing_transaction_repo = billing_transaction_repo
        self.apikey_service = apikey_service

    async def post(
        self,
        org_id: str,
        project_id: int,
        api_key_id: int,
        req: PostRequest,
    ) -> Result[UUID, SpendingLimitExceeded]:
        """Reserve spending capacity before a request is processed.

        Returns Ok(hold_uuid) on success.
        """
        org_id = ping["organization_id"]
        project_id = ping["project_id"]
        billing_period = _current_billing_period()
        hold_amount = _to_decimal(ping["amount"])

        async with self.session_manager.get_session() as session:
            spending_limit_rows = await self.spending_limit_repo.get(
                session, org_id, project_id, SpendingLimitType.MONTHLY
            )
            project_limit = None
            org_limit = None
            for row in spending_limit_rows:
                if row.project_id == project_id:
                    project_limit = row.limit
                elif row.project_id is None:
                    org_limit = row.limit

            # Returns None if project_limit would be exceeded OR period finalized.
            agg = await self.usage_agg_repo.holdAggregate(
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

    async def capture(
        self,
        org_id: str,
        project_id: int,
        api_key_id: int,
        transaction_uid: UUID,
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
        billing_period: str = hold["billing_period"]

        hold_amount = _to_decimal(hold["hold_amount"])
        real = _to_decimal(real_amount)
        # delta ≤ 0 in the typical case (hold over-estimated real cost)
        delta = real - hold_amount

        async with self.session_manager.get_session() as session:
            agg = await self.usage_agg_repo.releaseAggregate(
                session, project_id, org_id, billing_period, delta
            )
            if agg is None:
                # Finalized period — should never happen in normal flow.
                self.logger.error(
                    "billing.release.finalized_aggregate",
                    hold_uuid=str(hold_uuid),
                    project_id=project_id,
                    billing_period=billing_period,
                    org_id=org_id,
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
