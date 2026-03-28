from src.db.factories import AsyncSessionManager
from src.management.billing.dtos import PostRequest, ScaledAmount
from src.shared.utils.redis_lock import redis_lock
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
import asyncio
from uuid import UUID, uuid4
from typing import Any, Callable, Awaitable, TypedDict, cast
from decimal import Decimal
from calendar import c
from datetime import UTC, datetime, timezone

from pyrusult import Ok, Err, Result
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


def _current_billing_period() -> datetime:
    """Return the current UTC billing period in YYYY-MM format."""
    return datetime.now(UTC).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )


def _to_decimal(amount: ScaledAmount) -> Decimal:
    """Convert a ScaledAmount to a Python Decimal.

    Decimal.scaleb(n) multiplies by 10^n — exact integer arithmetic, no float.
    """
    return Decimal(amount["value"]).scaleb(-amount["scale"])


def _to_int(amount: Decimal, scale: int) -> int:
    """Convert a Decimal amount to an integer representation given a scale."""
    return int((amount * (10**scale)).to_integral_value())


class ProjectNotFound(RecoverableError):
    status = 404
    code = "project_not_found"
    title = "Project Not Found"
    detail = "One or more project UUIDs were not found in the organization."

    def __init__(self, message: str):
        super().__init__()
        self.message = message


LUA_SCRIPTS_CHECK_AND_REFRESH_SPENDING_LIMIT = """
-- KEYS[1] = project spending limit key
-- KEYS[2] = org spending limit key
-- ARGV[1] = new TTL in seconds for the spending limit keys (refresh on access)

-- Get current spending limits
local project_limit = redis.call("GET", KEYS[1])
local org_limit = redis.call("GET", KEYS[2])
-- Check if limits exist
if not project_limit or not org_limit then
    return 0
end
-- Refresh TTLs
redis.call("EXPIRE", KEYS[1], ARGV[1])
redis.call("EXPIRE", KEYS[2], ARGV[1])
return 1
"""

LUA_SCRIPT_ADD_USAGE_AND_CHECK_LIMIT = """
-- KEYS[1] = project spending limit key
-- KEYS[2] = org spending limit key
-- KEYS[3] = project usage key
-- KEYS[4] = org usage key
-- ARGV[1] = usage to add (integer)
-- Get current spending limits
local project_limit = tonumber(redis.call("GET", KEYS[1]))
local org_limit = tonumber(redis.call("GET", KEYS[2]))
-- Get current usage
local project_usage = tonumber(redis.call("GET", KEYS[3]) or "0")
local org_usage = tonumber(redis.call("GET", KEYS[4]) or "0")
-- Calculate new usage
local new_project_usage = project_usage + tonumber(ARGV[1])
local new_org_usage = org_usage + tonumber(ARGV[1])
-- Check against limits (if limit is -1, it means no limit)
if (project_limit ~= -1 and new_project_usage > project_limit) or (org_limit ~= -1 and new_org_usage > org_limit) then
    return 0
end
-- Update usage
redis.call("SET", KEYS[3], new_project_usage)
redis.call("SET", KEYS[4], new_org_usage)
return 1
"""


class BillingTransactionService:
    """Implements the two-phase HOLD / RELEASE billing protocol."""

    _HOLD_KEY = "billing:hold:{uuid}"
    _HOLD_TTL = 3600  # seconds
    _PROJECT_SPENDING_LIMIT_KEY = (
        "billing:spending_limit:{org_id}:proj:{project_id}"
    )
    _ORG_SPENDING_LIMIT_KEY = "billing:spending_limit:{org_id}"

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

    async def redis_check_or_load[T](
        self,
        lock_id: str,
        lock_ttl: int,
        lock_blocking_timeout: int,
        checker: Callable[[], Awaitable[bool]],
        loader: Callable[[], Awaitable[T]],
        setter: Callable[[T], Awaitable[None]],
        retry_times: int = 3,
    ) -> bool:
        """Helper to get a value from Redis or load it using the provided loader function."""
        for _ in range(retry_times):
            if await checker():
                return True
            async with redis_lock(
                self.redis,
                f"billing:redis_get_or_load_lock:{lock_id}",
                lock_ttl=lock_ttl,
                blocking_timeout=lock_blocking_timeout,
            ) as lock_acquired:
                if not lock_acquired:
                    # Failed to acquire lock, likely another process is loading the value. Wait and retry.
                    await asyncio.sleep(0.2)
                    continue

                # Double-check after acquiring the lock
                if await checker():
                    return True

                # Load the value using the provided loader function
                try:
                    loaded_value = await loader()
                    await setter(loaded_value)
                except Exception as e:
                    await asyncio.sleep(
                        0.2
                    )  # Sleep before retrying on loader failure
                    continue
                return True
        return False

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
        billing_period = _current_billing_period()
        hold_amount = _to_decimal(req.amount)

        async def check_limits() -> bool:
            is_existed = await cast(
                Awaitable[int],
                self.redis.eval(
                    LUA_SCRIPTS_CHECK_AND_REFRESH_SPENDING_LIMIT,
                    2,
                    self._PROJECT_SPENDING_LIMIT_KEY.format(
                        org_id=org_id, project_id=project_id
                    ),
                    self._ORG_SPENDING_LIMIT_KEY.format(org_id=org_id),
                    self._HOLD_TTL,
                ),
            )
            return is_existed == 1

        async def load_limits_from_db():
            async with self.session_manager.get_session() as session:
                rows = await self.spending_limit_repo.get(
                    session, org_id, project_id, SpendingLimitType.MONTHLY
                )
                project_limit = None
                org_limit = None
                for row in rows:
                    if row.project_id == project_id:
                        project_limit = row.limit
                    elif row.project_id is None:
                        org_limit = row.limit
                return project_limit, org_limit

        async def save_limits_to_redis(
            limit_tuple: tuple[Decimal | None, Decimal | None],
        ):
            project_limit, org_limit = limit_tuple
            async with self.redis.pipeline() as pipe:
                pipe.set(
                    self._PROJECT_SPENDING_LIMIT_KEY.format(
                        org_id=org_id, project_id=project_id
                    ),
                    _to_int(project_limit, 8)
                    if project_limit is not None
                    else -1,
                    ex=self._HOLD_TTL,
                )
                pipe.set(
                    self._ORG_SPENDING_LIMIT_KEY.format(org_id=org_id),
                    _to_int(org_limit, 8) if org_limit is not None else -1,
                    ex=self._HOLD_TTL,
                )
                await pipe.execute()

        success = await self.redis_check_or_load(
            lock_id=f"spending_limit:{org_id}:{project_id}",
            lock_ttl=10,
            lock_blocking_timeout=5,
            checker=check_limits,
            loader=load_limits_from_db,
            setter=save_limits_to_redis,
            retry_times=3,
        )

        if not success:
            pass

        is_allowed = await cast(
            Awaitable[int],
            self.redis.eval(
                LUA_SCRIPT_ADD_USAGE_AND_CHECK_LIMIT,
                4,
                self._PROJECT_SPENDING_LIMIT_KEY.format(
                    org_id=org_id, project_id=project_id
                ),
                self._ORG_SPENDING_LIMIT_KEY.format(org_id=org_id),
                f"billing:usage:{org_id}:proj:{project_id}",
                f"billing:usage:{org_id}",
                _to_int(hold_amount, 8),
            ),
        )
        if is_allowed == 0:
            self.logger.warning(
                "billing.spending_limit_exceeded",
                project_id=project_id,
                billing_period=billing_period,
                org_id=org_id,
            )
            return Err(SpendingLimitExceeded())

        hold_uuid = uuid4()
        hold_record: _HoldRecord = {
            "project_id": project_id,
            "org_id": org_id,
            "apikey_id": api_key_id,
            "hold_amount": req.amount,
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
