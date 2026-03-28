from src.db.factories import AsyncSessionManager
from src.shared.utils.redis import redis_check_or_load
from src.management.billing.dtos import PostRequest, ScaledAmount
from src.management.billing.type import AggregatePeriod
from src.shared.utils.uuid_utils import uuid7
from src.management.billing.models import SpendingLimitType, BillingTransaction
from src.management.api_keys.services import ApiKeyService
from src.shared.custom_types.error_exception import (
    RecoverableError,
    InternalServiceError,
)
from src.management.billing.repositories.transaction_repo import (
    TransactionRepository,
)
from src.management.billing.repositories.spending_limit_repo import (
    SpendingLimitRepository,
)

import json
from uuid import UUID, uuid4
from typing import Awaitable, TypedDict, cast
from decimal import Decimal
from calendar import c
from datetime import UTC, datetime

from pyrusult import Ok, Err, Result
from sqlalchemy import func
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger


class SpendingLimitExceeded(RecoverableError):
    status = 403
    code = "spending_limit_exceeded"
    title = "Spending Limit Exceeded"
    detail = "The request would exceed the configured spending limit."


class TransactionNotFound(RecoverableError):
    status = 404
    code = "transaction_not_found"
    title = "Transaction Not Found"
    detail = "The billing transaction UUID does not exist or has expired."


class TransactionExpiredOrCaptured(RecoverableError):
    status = 400
    code = "transaction_expired_or_captured"
    title = "Transaction Expired or Already Captured"
    detail = "The billing transaction has either expired or has already been captured and cannot be captured again."


class _TransactionRecord(TypedDict):
    project_id: int
    org_id: str
    apikey_id: int
    amount: ScaledAmount


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


LUA_SCRIPT_ADD_USAGE_AND_CHECK_LIMIT = """
-- KEYS[1] = project spending limit key
-- KEYS[2] = org spending limit key
-- KEYS[3] = project usage key
-- KEYS[4] = org usage key
-- KEYs[5] = transaction key
-- ARGV[1] = usage to add (integer)
-- ARGV[2] = transaction json string
-- ARGV[3] = cache TTL in seconds
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
redis.call("SET", KEYS[3], new_project_usage, "EX", ARGV[3])
redis.call("SET", KEYS[4], new_org_usage, "EX", ARGV[3])
redis.call("SET", KEYS[5], ARGV[2], "EX", ARGV[3])
return 1
"""

LUA_SCRIPT_UNDO_USAGE = """
-- KEYS[1] = project usage key
-- KEYS[2] = org usage key
-- KEYS[3] = transaction key
-- ARGV[1] = usage to subtract (integer)
-- Get current usage
local project_usage = tonumber(redis.call("GET", KEYS[1]) or "0")
local org_usage = tonumber(redis.call("GET", KEYS[2]) or "0")
-- Calculate new usage
local new_project_usage = project_usage - tonumber(ARGV[1])
local new_org_usage = org_usage - tonumber(ARGV[1])
-- Update usage (ensure it doesn't go below 0)
redis.call("SET", KEYS[1], math.max(new_project_usage, 0))
redis.call("SET", KEYS[2], math.max(new_org_usage, 0))
redis.call("DEL", KEYS[3])
return 1
"""

LUA_SCRIPT_CAPTURE_AND_UPDATE_USAGE = """
-- KEYS[1] = project usage key
-- KEYS[2] = org usage key
-- KEYS[3] = transaction key
-- ARGV[1] = delta to add (real_amount - hold_amount, can be negative)
-- Get current usage
local project_usage = tonumber(redis.call("GET", KEYS[1]) or "0")
local org_usage = tonumber(redis.call("GET", KEYS[2]) or "0")
-- Calculate new usage
local new_project_usage = project_usage + tonumber(ARGV[1])
local new_org_usage = org_usage + tonumber(ARGV[1])
-- Update usage (ensure it doesn't go below 0)
redis.call("SET", KEYS[1], math.max(new_project_usage, 0))
redis.call("SET", KEYS[2], math.max(new_org_usage, 0))
redis.call("DEL", KEYS[3])
return 1
"""


class TransactionService:
    _CACHE_TTL = 3600  # seconds
    _TRANSACTION_KEY = "billing:trx:{uuid}"
    _PROJECT_SPENDING_LIMIT_KEY = (
        "billing:spending_limit:{org_id}:proj:{project_id}"
    )
    _ORG_SPENDING_LIMIT_KEY = "billing:spending_limit:{org_id}"
    _ORG_USAGE_KEY = "billing:usage:{org_id}"
    _PROJECT_USAGE_KEY = "billing:usage:{org_id}:proj:{project_id}"

    def __init__(
        self,
        logger: BoundLogger,
        session_manager: AsyncSessionManager,
        redis: Redis,
        spending_limit_repo: SpendingLimitRepository,
        transaction_repo: TransactionRepository,
        apikey_service: ApiKeyService,
    ) -> None:
        self.logger = logger
        self.session_manager = session_manager
        self.redis = redis
        self.spending_limit_repo = spending_limit_repo
        self.transaction_repo = transaction_repo
        self.apikey_service = apikey_service

    async def post(
        self,
        org_id: str,
        project_id: int,
        api_key_id: int,
        req: PostRequest,
    ) -> Result[UUID, SpendingLimitExceeded | InternalServiceError]:
        """Reserve spending capacity before a request is processed.

        Returns Ok(transaction_uuid) on success.
        """
        billing_period = _current_billing_period()
        amount = _to_decimal(req.amount)
        transaction_uuid = uuid7()
        transaction_record: _TransactionRecord = {
            "project_id": project_id,
            "org_id": org_id,
            "apikey_id": api_key_id,
            "amount": req.amount,
        }

        trx_key = self._TRANSACTION_KEY.format(uuid=transaction_uuid)
        org_limit_key = self._ORG_SPENDING_LIMIT_KEY.format(org_id=org_id)
        project_limit_key = self._PROJECT_SPENDING_LIMIT_KEY.format(
            org_id=org_id, project_id=project_id
        )
        org_usage_key = self._ORG_USAGE_KEY.format(org_id=org_id)
        project_usage_key = self._PROJECT_USAGE_KEY.format(
            org_id=org_id, project_id=project_id
        )

        async def check_project_limits(
            redis: Redis,
        ) -> bool:
            is_existed = await cast(
                Awaitable[bool],
                redis.expire(
                    project_limit_key,
                    self._CACHE_TTL,
                    xx=True,  # only set if key exists
                ),
            )
            return is_existed

        async def check_org_limits(redis: Redis) -> bool:

            is_existed = await cast(
                Awaitable[bool],
                redis.expire(
                    org_limit_key,
                    self._CACHE_TTL,
                ),
            )
            return is_existed

        async def check_org_usage(redis: Redis) -> bool:
            is_existed = await cast(
                Awaitable[bool],
                redis.expire(org_usage_key, self._CACHE_TTL, xx=True),
            )
            return is_existed

        async def check_project_usage(redis: Redis) -> bool:
            is_existed = await cast(
                Awaitable[bool],
                redis.expire(project_usage_key, self._CACHE_TTL, xx=True),
            )
            return is_existed

        async def load_project_limits_from_db() -> Decimal | None:
            async with self.session_manager.get_session() as session:
                limit = await self.spending_limit_repo.getProjectLimits(
                    session, org_id, project_id, SpendingLimitType.MONTHLY
                )
                return limit.limit if limit else None

        async def load_org_limits_from_db() -> Decimal | None:
            async with self.session_manager.get_session() as session:
                limit = await self.spending_limit_repo.getOrgLimits(
                    session, org_id, SpendingLimitType.MONTHLY
                )
                return limit.limit if limit else None

        async def load_org_usage_from_db() -> Decimal:
            async with self.session_manager.get_session() as session:
                usage = await self.transaction_repo.sumByPeriodByOrganizations(
                    session,
                    [org_id],
                    billing_period,
                    None,
                    AggregatePeriod.MONTHLY,
                    period_scale=1,
                )
                return (
                    usage[0]["total_amount"]
                    if usage and len(usage) > 0
                    else Decimal(0)
                )

        async def load_project_usage_from_db() -> Decimal:
            async with self.session_manager.get_session() as session:
                usage = await self.transaction_repo.sumByPeriodByProjects(
                    session,
                    [project_id],
                    org_id,
                    billing_period,
                    None,
                    AggregatePeriod.MONTHLY,
                    period_scale=1,
                )
                return (
                    usage[0]["total_amount"]
                    if usage and len(usage) > 0
                    else Decimal(0)
                )

        async def save_project_limits_to_redis(
            redis: Redis, project_limit: Decimal | None
        ):
            await redis.set(
                project_limit_key,
                _to_int(project_limit, 8) if project_limit is not None else -1,
                ex=self._CACHE_TTL,
            )

        async def save_org_limits_to_redis(
            redis: Redis, org_limit: Decimal | None
        ):
            await redis.set(
                org_limit_key,
                _to_int(org_limit, 8) if org_limit is not None else -1,
                ex=self._CACHE_TTL,
            )

        async def save_org_usage_to_redis(redis: Redis, org_usage: Decimal):
            await redis.set(
                org_usage_key,
                _to_int(org_usage, 8),
                ex=self._CACHE_TTL,
            )

        async def save_project_usage_to_redis(
            redis: Redis, project_usage: Decimal
        ):
            await redis.set(
                project_usage_key,
                _to_int(project_usage, 8),
                ex=self._CACHE_TTL,
            )

        success = await redis_check_or_load(
            redis=self.redis,
            lock_id=f"spending_limit:{org_id}:{project_id}",
            lock_ttl=10,
            lock_blocking_timeout=5,
            checker=check_project_limits,
            loader=load_project_limits_from_db,
            setter=save_project_limits_to_redis,
            retry_times=3,
        )

        if not success:
            return Err(
                InternalServiceError(
                    message="Failed to load project spending limits. Please try again."
                )
            )

        success = await redis_check_or_load(
            redis=self.redis,
            lock_id=f"spending_limit:{org_id}",
            lock_ttl=10,
            lock_blocking_timeout=5,
            checker=check_org_limits,
            loader=load_org_limits_from_db,
            setter=save_org_limits_to_redis,
            retry_times=3,
        )

        if not success:
            return Err(
                InternalServiceError(
                    message="Failed to load organization spending limits. Please try again."
                )
            )

        success = await redis_check_or_load(
            redis=self.redis,
            lock_id=f"usage:{org_id}",
            lock_ttl=10,
            lock_blocking_timeout=5,
            checker=check_org_usage,
            loader=load_org_usage_from_db,
            setter=save_org_usage_to_redis,
            retry_times=3,
        )

        if not success:
            return Err(
                InternalServiceError(
                    message="Failed to load organization usage. Please try again."
                )
            )

        success = await redis_check_or_load(
            redis=self.redis,
            lock_id=f"usage:{org_id}:{project_id}",
            lock_ttl=10,
            lock_blocking_timeout=5,
            checker=check_project_usage,
            loader=load_project_usage_from_db,
            setter=save_project_usage_to_redis,
            retry_times=3,
        )

        if not success:
            return Err(
                InternalServiceError(
                    message="Failed to load project usage. Please try again."
                )
            )

        is_allowed = await cast(
            Awaitable[int],
            self.redis.eval(
                LUA_SCRIPT_ADD_USAGE_AND_CHECK_LIMIT,
                4,
                project_limit_key,
                org_limit_key,
                project_usage_key,
                org_usage_key,
                trx_key,
                str(_to_int(amount, 8)),
                json.dumps(transaction_record),
                self._CACHE_TTL,
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
        try:
            async with self.session_manager.get_session() as session:
                await self.transaction_repo.addTransaction(
                    session=session,
                    transaction_id=transaction_uuid,
                    apikey_id=api_key_id,
                    project_id=project_id,
                    org_id=org_id,
                    amount=amount,
                    details=req.details,
                    capture=req.capture,
                )
                await session.commit()
        except Exception as e:
            # Roll back the Redis usage if DB transaction fails
            await cast(
                Awaitable[int],
                self.redis.eval(
                    LUA_SCRIPT_UNDO_USAGE,
                    3,
                    project_usage_key,
                    org_usage_key,
                    trx_key,
                    str(_to_int(amount, 8)),
                ),
            )
            return Err(
                InternalServiceError(
                    message="Failed to record billing transaction. Please try again."
                )
            )

        self.logger.info(
            "billing.transaction.posted",
            transaction_uuid=str(transaction_uuid),
            project_id=project_id,
            billing_period=billing_period,
        )
        return Ok(transaction_uuid)

    async def capture(
        self,
        org_id: str,
        project_id: int,
        api_key_id: int,
        transaction_uid: UUID,
        real_amount: ScaledAmount,
    ) -> Result[bool, TransactionNotFound | TransactionExpiredOrCaptured]:
        """Commit the actual charge after a request completes.

        Returns Ok(True) on success.
        """
        transaction_key = self._TRANSACTION_KEY.format(uuid=transaction_uid)
        raw = await self.redis.get(transaction_key)
        if raw is None:
            return Err(TransactionNotFound())

        trx: _TransactionRecord = json.loads(raw)

        amount = _to_decimal(trx["amount"])
        real = _to_decimal(real_amount)
        # delta ≤ 0 in the typical case (hold over-estimated real cost)
        delta = real - amount

        async with self.session_manager.get_session() as session:
            updated_tx = await self.transaction_repo.captureTransaction(
                session=session,
                transaction_id=transaction_uid,
                real_amount=real,
            )
            if not updated_tx:
                return Err(TransactionExpiredOrCaptured())
            await session.commit()

        await cast(
            Awaitable[int],
            self.redis.eval(
                LUA_SCRIPT_CAPTURE_AND_UPDATE_USAGE,
                3,
                self._PROJECT_USAGE_KEY.format(
                    org_id=org_id, project_id=project_id
                ),
                self._ORG_USAGE_KEY.format(org_id=org_id),
                transaction_key,
                str(_to_int(delta, 8)),
            ),
        )

        self.logger.info(
            "billing.transaction.captured",
            transaction_uuid=str(transaction_uid),
            project_id=project_id,
            org_id=org_id,
            api_key_id=api_key_id,
            pre_amount=str(amount),
            real_amount=str(real),
            delta=str(delta),
        )
        return Ok(True)
