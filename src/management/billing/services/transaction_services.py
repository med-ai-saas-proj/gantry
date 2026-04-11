from src.db.factories import AsyncSessionManager
from src.shared.utils.redis import redis_get_or_load
from src.shared.utils.uuid_utils import uuid7
from src.management.billing.utils import (
    _to_decimal,
    _decimal_to_int,
    _int_to_decimal,
    _get_billing_period,
    _get_next_billing_period,
)
from src.management.api_keys.services import ApiKeyService
from src.shared.custom_types.error_exception import (
    RecoverableError,
    InternalServiceError,
)

from ..dtos import (
    PostRequest,
    ScaledAmount,
    TransactionInfoResponse,
)
from ..type import AggregatePeriod
from ..models import SpendingLimitType, BillingTransaction
from ..repositories.transaction_repo import (
    TransactionRepository,
)
from ..repositories.spending_limit_repo import (
    SpendingLimitRepository,
)

import json
import asyncio
from uuid import UUID, uuid4
from typing import Sequence, Awaitable, TypedDict, cast
from decimal import Decimal
from datetime import UTC, datetime, timedelta

from pyrusult import Ok, Err, Result, ResultStatus
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger
from sqlalchemy.ext.asyncio import AsyncSession


class SpendingLimitExceeded(RecoverableError):
    status = 403
    code = "spending_limit_exceeded"
    title = "Spending Limit Exceeded"
    detail = "The request would exceed the configured spending limit."


class TransactionNotFoundOrExpiredOrCaptured(RecoverableError):
    status = 400
    code = "transaction_not_found_or_expired_or_captured"
    title = "Transaction Not Found or Expired or Already Captured"
    detail = "The billing transaction was not found, has expired, or has already been captured and cannot be captured again."


class TransactionInProgress(RecoverableError):
    status = 409
    code = "transaction_in_progress"
    title = "Transaction In Progress"
    detail = "Another request with the same idempotency key is currently being processed. Please retry after some time."


class TransactionNotFound(RecoverableError):
    status = 404
    code = "transaction_not_found"
    title = "Transaction Not Found"
    detail = "The billing transaction was not found."


class _TransactionRecord(TypedDict):
    project_id: int
    org_id: str
    apikey_id: int
    amount: ScaledAmount
    billing_period: str


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
-- KEYS[5] = transaction key
-- KEYS[6] = idempotency key
-- ARGV[1] = usage to add (integer)
-- ARGV[2] = transaction json string
-- ARGV[3] = transaction id
-- ARGV[4] = cache TTL in seconds
-- ARGV[5] = idempotency key TTL in seconds
local existed_idempotency = redis.call("GET", KEYS[6])
-- If idempotency key exists and not pending, return the existing transaction ID to ensure idempotency
if existed_idempotency then
    return existed_idempotency
end
-- Get current spending limits
local project_limit = tonumber(redis.call("GET", KEYS[1]))
local org_limit = tonumber(redis.call("GET", KEYS[2]))
-- Get current usage
local project_usage = tonumber(redis.call("GET", KEYS[3]) or "0")
local org_usage = tonumber(redis.call("GET", KEYS[4]) or "0")
-- check existed
if project_limit == nil or org_limit == nil or project_usage == nil or org_usage == nil then
    return redis.error_reply("Required limits or usage not loaded in cache")
end
-- Calculate new usage
local new_project_usage = project_usage + tonumber(ARGV[1])
local new_org_usage = org_usage + tonumber(ARGV[1])
-- Check against limits (if limit is -1, it means no limit)
if (project_limit ~= -1 and new_project_usage > project_limit) or (org_limit ~= -1 and new_org_usage > org_limit) then
    return 0
end
-- Update usage
redis.call("SET", KEYS[3], new_project_usage, "EX", ARGV[4])
redis.call("SET", KEYS[4], new_org_usage, "EX", ARGV[4])
redis.call("SET", KEYS[5], ARGV[2], "EX", ARGV[4])
redis.call("SET", KEYS[6], "pending:" .. ARGV[3], "EX", ARGV[5])
return ARGV[3]
"""

LUA_SCRIPT_UNDO_USAGE = """
-- KEYS[1] = project usage key
-- KEYS[2] = org usage key
-- KEYS[3] = transaction key
-- KEYS[4] = idempotency key
-- ARGV[1] = usage to subtract (integer)
-- ARGV[2] = transaction id
-- ARGV[3] = cache TTL in seconds
-- Get current usage
local project_usage = tonumber(redis.call("GET", KEYS[1]) or "0")
local org_usage = tonumber(redis.call("GET", KEYS[2]) or "0")
-- check existed
if project_usage == nil or org_usage == nil then
    return redis.error_reply("Required usage not loaded in cache")
end
-- Calculate new usage
local new_project_usage = project_usage - tonumber(ARGV[1])
local new_org_usage = org_usage - tonumber(ARGV[1])
-- Update usage (ensure it doesn't go below 0)
redis.call("SET", KEYS[1], math.max(new_project_usage, 0), "EX", ARGV[3])
redis.call("SET", KEYS[2], math.max(new_org_usage, 0), "EX", ARGV[3])
redis.call("DEL", KEYS[3])
local existed_idempotency = redis.call("GET", KEYS[4])
if existed_idempotency and (existed_idempotency == ARGV[2] or existed_idempotency == "pending:" .. ARGV[2]) then
    redis.call("DEL", KEYS[4])
end
return 1
"""

LUA_SCRIPT_CAPTURE_AND_UPDATE_USAGE = """
-- KEYS[1] = project usage key
-- KEYS[2] = org usage key
-- KEYS[3] = transaction key
-- ARGV[1] = delta to add (real_amount - hold_amount, can be negative)
-- ARGV[2] = cache TTL in seconds
-- Get current usage
local project_usage = tonumber(redis.call("GET", KEYS[1]) or "0")
local org_usage = tonumber(redis.call("GET", KEYS[2]) or "0")
-- check existed
if project_usage == nil or org_usage == nil then
    return redis.error_reply("Required usage not loaded in cache")
end
-- Calculate new usage
local new_project_usage = project_usage + tonumber(ARGV[1])
local new_org_usage = org_usage + tonumber(ARGV[1])
-- Update usage (ensure it doesn't go below 0)
redis.call("SET", KEYS[1], math.max(new_project_usage, 0), "EX", ARGV[2])
redis.call("SET", KEYS[2], math.max(new_org_usage, 0), "EX", ARGV[2])
redis.call("DEL", KEYS[3])
return 1
"""


class TransactionService:
    _CACHE_TTL = 36000  # seconds
    _MAX_TRANSACTION_AGE = 3600  # seconds, after which a transaction is considered expired and cannot be captured
    _IDEMPOTENCY_KEY_TTL = (
        3600  # seconds, how long to keep idempotency keys in cache
    )
    _TRANSACTION_KEY = "billing:trx:{uuid}"
    _PROJECT_SPENDING_LIMIT_KEY = (
        "billing:spending_limit:{org_id}:proj:{project_id}"
    )
    _ORG_SPENDING_LIMIT_KEY = "billing:spending_limit:{org_id}"

    _ORG_USAGE_KEY = "billing:usage:{org_id}:{period}"
    _PROJECT_USAGE_KEY = "billing:usage:{org_id}:proj:{project_id}:{period}"

    _POST_IDEMPOTENCY_KEY = "billing:post_idempotency:{key}"

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

    async def getSpendingLimits(
        self, org_id: str, project_id: int
    ) -> Result[tuple[Decimal | None, Decimal | None], InternalServiceError]:
        """Get current spending limits for the organization and project."""
        org_limit_key = self._ORG_SPENDING_LIMIT_KEY.format(org_id=org_id)
        project_limit_key = self._PROJECT_SPENDING_LIMIT_KEY.format(
            org_id=org_id, project_id=project_id
        )
        res = await self._getOrLoadSpendingLimitsToRedis(
            org_id=org_id,
            project_id=project_id,
            org_limit_key=org_limit_key,
            project_limit_key=project_limit_key,
        )
        if res.status == ResultStatus.Err:
            return res.into()
        org_limit_raw, project_limit_raw = res.unwrap()
        org_limit = (
            _int_to_decimal(int(org_limit_raw), 8)
            if org_limit_raw != "-1"
            else None
        )
        project_limit = (
            _int_to_decimal(int(project_limit_raw), 8)
            if project_limit_raw != "-1"
            else None
        )
        return Ok((project_limit, org_limit))

    async def getUsage(
        self, org_id: str, project_id: int, ref_time: datetime
    ) -> Result[tuple[Decimal, Decimal], InternalServiceError]:
        """Get current usage for the organization and project in the billing period."""
        billing_period = _get_billing_period(ref_time)
        org_usage_key = self._ORG_USAGE_KEY.format(
            org_id=org_id, period=billing_period.strftime("%Y-%m")
        )
        project_usage_key = self._PROJECT_USAGE_KEY.format(
            org_id=org_id,
            project_id=project_id,
            period=billing_period.strftime("%Y-%m"),
        )
        res = await self._getOrLoadUsageToRedis(
            org_id=org_id,
            project_id=project_id,
            billing_period=billing_period,
            org_usage_key=org_usage_key,
            project_usage_key=project_usage_key,
        )
        if res.status == ResultStatus.Err:
            return res.into()
        org_usage_raw, project_usage_raw = res.unwrap()
        org_usage = _int_to_decimal(int(org_usage_raw), 8)
        project_usage = _int_to_decimal(int(project_usage_raw), 8)
        return Ok((org_usage, project_usage))

    async def _getOrLoadSpendingLimitsToRedis(
        self,
        org_id: str,
        project_id: int,
        org_limit_key: str,
        project_limit_key: str,
    ) -> Result[tuple[str, str], InternalServiceError]:
        async def get_project_limits(
            redis: Redis,
        ) -> str | None:
            v = await cast(
                Awaitable[str | None],
                redis.getex(
                    project_limit_key,
                    ex=self._CACHE_TTL,
                ),
            )
            return v

        async def get_org_limits(redis: Redis) -> str | None:
            v = await cast(
                Awaitable[str | None],
                redis.getex(
                    org_limit_key,
                    ex=self._CACHE_TTL,
                ),
            )
            return v

        async def load_project_limits_from_db(
            session: AsyncSession,
        ) -> str:
            limit = await self.spending_limit_repo.getProjectLimits(
                session, org_id, project_id, SpendingLimitType.MONTHLY
            )
            return str(_decimal_to_int(limit, 8)) if limit is not None else "-1"

        async def load_org_limits_from_db(
            session: AsyncSession,
        ) -> str:
            limit = await self.spending_limit_repo.getOrgLimits(
                session, org_id, SpendingLimitType.MONTHLY
            )
            return str(_decimal_to_int(limit, 8)) if limit is not None else "-1"

        async def save_project_limits_to_redis(
            redis: Redis, project_limit: str
        ):
            await redis.set(
                project_limit_key,
                project_limit,
                ex=self._CACHE_TTL,
            )

        async def save_org_limits_to_redis(redis: Redis, org_limit: str):
            await redis.set(
                org_limit_key,
                org_limit,
                ex=self._CACHE_TTL,
            )

        org_limit, project_limit = await asyncio.gather(
            redis_get_or_load(
                redis=self.redis,
                session_manager=self.session_manager,
                lock_id=f"spending_limit:{org_id}",
                lock_ttl=10,
                lock_blocking_timeout=5,
                getter=get_org_limits,
                loader=load_org_limits_from_db,
                setter=save_org_limits_to_redis,
                retry_times=3,
            ),
            redis_get_or_load(
                redis=self.redis,
                session_manager=self.session_manager,
                lock_id=f"spending_limit:{org_id}:{project_id}",
                lock_ttl=10,
                lock_blocking_timeout=5,
                getter=get_project_limits,
                loader=load_project_limits_from_db,
                setter=save_project_limits_to_redis,
                retry_times=3,
            ),
        )

        if org_limit is None:
            return Err(
                InternalServiceError(
                    message="Failed to load organization spending limits. Please try again."
                )
            )

        if project_limit is None:
            return Err(
                InternalServiceError(
                    message="Failed to load project spending limits. Please try again."
                )
            )
        return Ok((org_limit, project_limit))

    async def _getOrLoadUsageToRedis(
        self,
        org_id: str,
        project_id: int,
        billing_period: datetime,
        org_usage_key: str,
        project_usage_key: str,
    ) -> Result[tuple[str, str], InternalServiceError]:
        next_billing_period = _get_next_billing_period(billing_period)

        async def get_org_usage(redis: Redis) -> str | None:
            v = await cast(
                Awaitable[str | None],
                redis.getex(
                    org_usage_key,
                    ex=self._CACHE_TTL,
                ),
            )
            return v

        async def get_project_usage(redis: Redis) -> str | None:
            v = await cast(
                Awaitable[str | None],
                redis.getex(
                    project_usage_key,
                    ex=self._CACHE_TTL,
                ),
            )
            return v

        async def load_org_usage_from_db(
            session: AsyncSession,
        ) -> str:
            usage = await self.transaction_repo.sumByPeriodByOrganizations(
                session,
                [org_id],
                billing_period,
                next_billing_period,
                AggregatePeriod.MONTHLY,
                period_scale=1,
            )
            v = (
                usage[0]["total_amount"]
                if usage and len(usage) > 0
                else Decimal(0)
            )
            return str(_decimal_to_int(v, 8))

        async def load_project_usage_from_db(
            session: AsyncSession,
        ) -> str:
            usage = await self.transaction_repo.sumByPeriodByProjects(
                session,
                [project_id],
                org_id,
                billing_period,
                next_billing_period,
                AggregatePeriod.MONTHLY,
                period_scale=1,
            )
            v = (
                usage[0]["total_amount"]
                if usage and len(usage) > 0
                else Decimal(0)
            )
            return str(_decimal_to_int(v, 8))

        async def save_org_usage_to_redis(redis: Redis, org_usage: str):
            await redis.set(
                org_usage_key,
                org_usage,
                ex=self._CACHE_TTL,
            )

        async def save_project_usage_to_redis(redis: Redis, project_usage: str):
            await redis.set(
                project_usage_key,
                project_usage,
                ex=self._CACHE_TTL,
            )

        org_usage, project_usage = await asyncio.gather(
            redis_get_or_load(
                redis=self.redis,
                session_manager=self.session_manager,
                lock_id=f"usage:{org_id}",
                lock_ttl=10,
                lock_blocking_timeout=5,
                getter=get_org_usage,
                loader=load_org_usage_from_db,
                setter=save_org_usage_to_redis,
                retry_times=3,
            ),
            redis_get_or_load(
                redis=self.redis,
                session_manager=self.session_manager,
                lock_id=f"usage:{org_id}:{project_id}",
                lock_ttl=10,
                lock_blocking_timeout=5,
                getter=get_project_usage,
                loader=load_project_usage_from_db,
                setter=save_project_usage_to_redis,
                retry_times=3,
            ),
        )

        if org_usage is None:
            return Err(
                InternalServiceError(
                    message="Failed to load organization usage. Please try again."
                )
            )

        if project_usage is None:
            return Err(
                InternalServiceError(
                    message="Failed to load project usage. Please try again."
                )
            )
        return Ok((org_usage, project_usage))

    async def post(
        self,
        org_id: str,
        project_id: int,
        api_key_id: int,
        idempotency_key: str | None,
        req: PostRequest,
    ) -> Result[
        UUID,
        SpendingLimitExceeded | InternalServiceError | TransactionInProgress,
    ]:
        """Reserve spending capacity before a request is processed.

        Returns Ok(transaction_uuid) on success.
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        billing_period = _get_billing_period(now)
        amount = _to_decimal(req.amount)
        period_key = billing_period.strftime("%Y-%m")
        org_limit_key = self._ORG_SPENDING_LIMIT_KEY.format(org_id=org_id)
        project_limit_key = self._PROJECT_SPENDING_LIMIT_KEY.format(
            org_id=org_id, project_id=project_id
        )
        org_usage_key = self._ORG_USAGE_KEY.format(
            org_id=org_id, period=period_key
        )
        project_usage_key = self._PROJECT_USAGE_KEY.format(
            org_id=org_id, project_id=project_id, period=period_key
        )

        spending_limits_res = await self.getSpendingLimits(org_id, project_id)
        if spending_limits_res.status == ResultStatus.Err:
            return spending_limits_res.into()

        usage_res = await self._getOrLoadUsageToRedis(
            org_id=org_id,
            project_id=project_id,
            billing_period=billing_period,
            org_usage_key=org_usage_key,
            project_usage_key=project_usage_key,
        )
        if usage_res.status == ResultStatus.Err:
            return usage_res.into()

        idempotency_key = idempotency_key or str(uuid4())
        idempotency_cache_key = self._POST_IDEMPOTENCY_KEY.format(
            key=idempotency_key
        )

        transaction_uuid = uuid7()
        transaction_record: _TransactionRecord = {
            "project_id": project_id,
            "org_id": org_id,
            "apikey_id": api_key_id,
            "amount": req.amount,
            "billing_period": period_key,
        }

        trx_key = self._TRANSACTION_KEY.format(uuid=transaction_uuid)

        trx_res = await cast(
            Awaitable[int | str],
            self.redis.eval(
                LUA_SCRIPT_ADD_USAGE_AND_CHECK_LIMIT,
                6,
                project_limit_key,
                org_limit_key,
                project_usage_key,
                org_usage_key,
                trx_key,
                idempotency_cache_key,
                str(_decimal_to_int(amount, 8)),  # ARGV[1]
                json.dumps(transaction_record),  # ARGV[2]
                str(transaction_uuid),  # ARGV[3]
                self._CACHE_TTL,  # ARGV[4]
                self._IDEMPOTENCY_KEY_TTL,  # ARGV[5]
            ),
        )
        if trx_res == 0:
            self.logger.warning(
                "billing.spending_limit_exceeded",
                project_id=project_id,
                billing_period=billing_period,
                org_id=org_id,
            )
            return Err(SpendingLimitExceeded())

        trx_res = cast(str, trx_res)
        if trx_res.startswith("pending:"):
            async with self.session_manager.get_session() as session:
                existing_trx = await self.transaction_repo.getTransactionByUUID(
                    session, UUID(trx_res[len("pending:") :])
                )
                if existing_trx:
                    # likely the original request is successful but just haven't set the idempotency key in Redis yet
                    return Ok(existing_trx.uuid)

            self.logger.info(
                "billing.post_idempotent_request_in_progress",
                project_id=project_id,
                billing_period=billing_period,
                org_id=org_id,
                idempotency_key=idempotency_key,
            )
            return Err(TransactionInProgress())

        if trx_res != str(transaction_uuid):
            # This means the operation was not performed by this request, but another request with the same idempotency key. We can safely return success with the existing transaction UUID.
            self.logger.info(
                "billing.post_idempotent_request",
                project_id=project_id,
                billing_period=billing_period,
                org_id=org_id,
                idempotency_key=idempotency_key,
                existing_transaction_uuid=trx_res,
            )
            return Ok(UUID(trx_res))

        try:
            async with self.session_manager.get_session() as session:
                # use server time for created_at to ensure it's consistent with billing period calculation
                await self.transaction_repo.addTransaction(
                    session=session,
                    transaction_uid=transaction_uuid,
                    apikey_id=api_key_id,
                    project_id=project_id,
                    org_id=org_id,
                    amount=amount,
                    details=req.details,
                    capture=req.capture,
                    created_at=now,
                )
                await session.commit()
        except Exception as e:
            # Roll back the Redis usage if DB transaction fails
            await cast(
                Awaitable[int],
                self.redis.eval(
                    LUA_SCRIPT_UNDO_USAGE,
                    4,
                    project_usage_key,
                    org_usage_key,
                    trx_key,
                    idempotency_cache_key,
                    str(_decimal_to_int(amount, 8)),
                    str(transaction_uuid),
                    self._CACHE_TTL,
                ),
            )
            return Err(
                InternalServiceError(
                    message="Failed to record billing transaction. Please try again."
                )
            )

        await self.redis.set(
            idempotency_cache_key,
            str(transaction_uuid),
            ex=self._IDEMPOTENCY_KEY_TTL,
        )

        if req.capture:
            await self.redis.delete(trx_key)

        self.logger.info(
            "billing.transaction.posted",
            transaction_uuid=str(transaction_uuid),
            project_id=project_id,
            billing_period=billing_period,
            org_id=org_id,
            api_key_id=api_key_id,
            amount=str(amount),
            capture=req.capture,
        )
        return Ok(transaction_uuid)

    async def capture(
        self,
        org_id: str,
        project_id: int,
        api_key_id: int,
        transaction_uid: UUID,
        real_amount: ScaledAmount,
    ) -> Result[
        bool, TransactionNotFoundOrExpiredOrCaptured | InternalServiceError
    ]:
        """Commit the actual charge after a request completes.

        Returns Ok(True) on success.
        """
        transaction_key = self._TRANSACTION_KEY.format(uuid=transaction_uid)
        real = _to_decimal(real_amount)

        raw = await self.redis.get(transaction_key)
        if raw is None:
            async with self.session_manager.get_session() as session:
                trx_ = await self.transaction_repo.getTransactionByUUID(
                    session, transaction_uid
                )
                if not trx_:
                    return Err(TransactionNotFoundOrExpiredOrCaptured())
                amount = trx_.amount
                billing_period = _get_billing_period(trx_.created_at)
                billing_period_str = billing_period.strftime("%Y-%m")
        else:
            trx: _TransactionRecord = json.loads(raw)

            if (
                trx["org_id"] != org_id
                or trx["project_id"] != project_id
                or trx["apikey_id"] != api_key_id
            ):
                return Err(TransactionNotFoundOrExpiredOrCaptured())

            amount = _to_decimal(trx["amount"])
            billing_period_str = trx["billing_period"]
            billing_period = datetime.strptime(
                trx["billing_period"], "%Y-%m"
            ).replace(tzinfo=UTC)

        org_usage_key = self._ORG_USAGE_KEY.format(
            org_id=org_id, period=billing_period_str
        )
        project_usage_key = self._PROJECT_USAGE_KEY.format(
            org_id=org_id, project_id=project_id, period=billing_period_str
        )

        usage_res = await self._getOrLoadUsageToRedis(
            org_id=org_id,
            project_id=project_id,
            billing_period=billing_period,
            org_usage_key=org_usage_key,
            project_usage_key=project_usage_key,
        )
        if usage_res.status == ResultStatus.Err:
            return usage_res.into()

        # delta ≤ 0 in the typical case (hold over-estimated real cost)
        delta = real - amount
        async with self.session_manager.get_session() as session:
            updated_tx = await self.transaction_repo.captureTransaction(
                session=session,
                transaction_uid=transaction_uid,
                real_amount=real,
            )
            if not updated_tx:
                # likely means the transaction was already captured
                # but fail to update Redis cache in the previous capture attempt
                return Err(TransactionNotFoundOrExpiredOrCaptured())
            await session.commit()

        await cast(
            Awaitable[int],
            self.redis.eval(
                LUA_SCRIPT_CAPTURE_AND_UPDATE_USAGE,
                3,
                project_usage_key,
                org_usage_key,
                transaction_key,
                str(_decimal_to_int(delta, 8)),
                self._CACHE_TTL,
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

    async def get_transactions(
        self,
        org_id: str,
        project_uids: list[UUID] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Result[tuple[Sequence[TransactionInfoResponse], int], None]:
        """List transactions with optional filters (e.g. project_id, date range, etc.). Supports pagination."""

        async with self.session_manager.get_session() as session:
            (
                transactions,
                total,
            ) = await self.transaction_repo.getTransactionInfoList(
                session=session,
                org_id=org_id,
                project_uids=project_uids,
                start_date=start_date,
                end_date=end_date,
                offset=offset,
                limit=limit,
            )
            return Ok(
                (
                    [
                        TransactionInfoResponse(
                            transaction_uid=trx["transaction_uid"],
                            project_uid=trx["project_uid"],
                            amount=trx["amount"],
                            details=trx["details"],
                            date=trx["date"],
                            captured_at=trx["captured_at"],
                        )
                        for trx in transactions
                    ],
                    total,
                )
            )

    async def get_transaction_by_id(
        self, org_id: str, transaction_uid: UUID
    ) -> Result[TransactionInfoResponse, TransactionNotFound]:
        """Get transaction details by transaction UUID."""
        async with self.session_manager.get_session() as session:
            trx = await self.transaction_repo.getTransactionInfoByUUID(
                session=session,
                transaction_uid=transaction_uid,
                org_id=org_id,
            )
            if not trx:
                return Err(TransactionNotFound())
            return Ok(
                TransactionInfoResponse(
                    transaction_uid=trx["transaction_uid"],
                    project_uid=trx["project_uid"],
                    amount=trx["amount"],
                    details=trx["details"],
                    date=trx["date"],
                    captured_at=trx["captured_at"],
                )
            )

    async def closeExpiredTransactions(
        self, task_id: UUID, now: datetime
    ) -> None:
        """Close expired transactions that are not captured within the max transaction age."""
        expired_time = now - timedelta(seconds=self._MAX_TRANSACTION_AGE)

        async with self.session_manager.get_session() as session:
            expired_trxs = await self.transaction_repo.setTransactionsExpired(
                session=session, expiration_time=expired_time
            )
            session.expunge_all()  # detach all instances to prevent accidental use after commit
            await session.commit()

        if expired_trxs:
            self.logger.info(
                "billing.expire_transactions",
                count=len(expired_trxs),
                transaction_uuids=[str(trx.uuid) for trx in expired_trxs],
                task_id=str(task_id),
            )

    async def closeExpiredTransactionsTask(
        self,
        sleep_interval_seconds: int,
    ):
        while True:
            now = datetime.now(UTC).replace(tzinfo=None)
            task_id = uuid4()
            try:
                await self.closeExpiredTransactions(task_id, now)
            except Exception as e:
                self.logger.error(
                    "billing.close_expired_transactions_failed",
                    task_id=str(task_id),
                    error=str(e),
                )
            await asyncio.sleep(sleep_interval_seconds)
