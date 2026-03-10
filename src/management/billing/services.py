"""Core billing service — HOLD/RELEASE pattern.

Flow (see architecture diagram):

  HOLD (called by Service#1 before processing the request):
    1. Load effective monthly limit from Postgres (project → org → None).
    2. Atomically check Redis spending counter + increment via Lua script.
       Seeds the Redis key from Postgres aggregate on cache-miss.
    3. Persist hold record in Redis with TTL.
    4. Return hold UUID to the caller.
    → 403 SpendingLimitExceeded if over limit.

  RELEASE (called by Service#1 after computing the real cost):
    1. Load hold record from Redis by UUID.
    2. Adjust Redis aggregate atomically: subtract hold, add real_cost.
    3. Delete hold record from Redis.
    4. Upsert MonthlyAggregate in Postgres (source of truth).
    TODO(BILL-008): INSERT BillingTransaction into TimescaleDB.
"""

import json
from decimal import Decimal
from datetime import datetime, timezone
from typing import TypedDict
from uuid import UUID, uuid4

from redis.asyncio import Redis
from safe_result import Err, Ok, Result
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.stdlib import BoundLogger

from src.db.factories import AsyncSessionManager
from src.shared.custom_types.error_exception import RecoverableError

from .dtos import BillingPing, ScaledAmount
from .repositories import (
    MonthlyAggregateRepository,
    OrganizationSpendingLimitRepository,
    ProjectSpendingLimitRepository,
)

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
# Internal Redis record shape
# ---------------------------------------------------------------------------


class _HoldRecord(TypedDict):
    project_id: int
    org_id: str
    apikey_id: str
    amount_redis: int  # hold amount normalised to _REDIS_SCALE
    billing_period: str  # "YYYY-MM" — period active when HOLD was placed


# ---------------------------------------------------------------------------
# Module-level constants / helpers
# ---------------------------------------------------------------------------

# All amounts in Redis are stored as integers at this implicit scale.
# Scale 8 matches the Postgres Numeric(18, 8) columns.
_REDIS_SCALE = 8

# Lua script: atomically check spending + hold ≤ limit, then increment.
# Returns the new running total (int), or -1 if the limit would be exceeded.
#
# KEYS[1] = billing:agg:{project_id}:{period}
# ARGV[1] = hold amount  (int at _REDIS_SCALE)
# ARGV[2] = monthly limit (-1 means unlimited)
# ARGV[3] = postgres total (seeds the Redis key on cache-miss)
_HOLD_LUA = """
local current_raw = redis.call('GET', KEYS[1])
local current
if current_raw == false then
    current = tonumber(ARGV[3])
    redis.call('SET', KEYS[1], current)
else
    current = tonumber(current_raw)
end
local hold  = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
if limit >= 0 and (current + hold) > limit then
    return -1
end
redis.call('INCRBY', KEYS[1], hold)
return current + hold
"""


def _current_billing_period() -> str:
    """Return the current UTC billing period in YYYY-MM format."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _to_redis_int(value: int, scale: int) -> int:
    """Normalise a ScaledAmount to a Redis integer at _REDIS_SCALE.

    Truncates sub-micro-cent precision — acceptable for billing at this scale.
    """
    return int(Decimal(value) * Decimal(10) ** (_REDIS_SCALE - scale))


def _decimal_to_redis_int(amount: Decimal) -> int:
    """Convert a Postgres Decimal amount to a Redis integer at _REDIS_SCALE."""
    return int(amount * Decimal(10) ** _REDIS_SCALE)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BillingService:
    """Implements the two-phase HOLD / RELEASE billing protocol."""

    _AGG_KEY = "billing:agg:{project_id}:{period}"
    _HOLD_KEY = "billing:hold:{uuid}"
    _HOLD_TTL = 3600  # holds expire after 1 hour if never released

    def __init__(
        self,
        logger: BoundLogger,
        session_manager: AsyncSessionManager,
        redis: Redis,
        monthly_agg_repo: MonthlyAggregateRepository,
        project_limit_repo: ProjectSpendingLimitRepository,
        org_limit_repo: OrganizationSpendingLimitRepository,
    ) -> None:
        self.logger = logger
        self.session_manager = session_manager
        self.redis = redis
        self.monthly_agg_repo = monthly_agg_repo
        self.project_limit_repo = project_limit_repo
        self.org_limit_repo = org_limit_repo

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def hold(self, ping: BillingPing) -> Result[UUID, SpendingLimitExceeded]:
        """Reserve spending capacity before a request is processed.

        Returns Ok(hold_uuid) on success.
        Returns Err(SpendingLimitExceeded) if the hold would breach the limit.
        """
        org_id = ping["organization_id"]
        project_id = ping["project_id"]
        billing_period = _current_billing_period()

        hold_amount_redis = _to_redis_int(
            ping["amount"]["value"], ping["amount"]["scale"]
        )

        # Both DB reads share one session to avoid two round-trips.
        async with self.session_manager.get_session() as session:
            monthly_limit = await self._effective_monthly_limit(
                session, project_id, org_id
            )
            pg_agg = await self.monthly_agg_repo.getAggregate(
                session, project_id, billing_period
            )

        limit_redis = (
            _decimal_to_redis_int(monthly_limit) if monthly_limit is not None else -1
        )
        pg_total_redis = _decimal_to_redis_int(pg_agg.total_amount) if pg_agg else 0

        agg_key = self._AGG_KEY.format(project_id=project_id, period=billing_period)
        result = self.redis.eval(
            _HOLD_LUA,
            1,
            agg_key,
            hold_amount_redis,
            limit_redis,
            pg_total_redis,
        )

        if result == -1:
            return Err(SpendingLimitExceeded())

        hold_uuid = uuid4()
        hold_key = self._HOLD_KEY.format(uuid=hold_uuid)
        hold_record: _HoldRecord = {
            "project_id": project_id,
            "org_id": org_id,
            "apikey_id": ping["apikey_id"],
            "amount_redis": hold_amount_redis,
            "billing_period": billing_period,
        }
        await self.redis.set(hold_key, json.dumps(hold_record), ex=self._HOLD_TTL)

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
        Returns Err(HoldNotFound) if the hold UUID is unknown or expired.
        """
        hold_key = self._HOLD_KEY.format(uuid=hold_uuid)
        raw = await self.redis.get(hold_key)
        if raw is None:
            return Err(HoldNotFound())

        hold: _HoldRecord = json.loads(raw)
        project_id: int = hold["project_id"]
        hold_amount_redis: int = hold["amount_redis"]
        billing_period: str = hold["billing_period"]

        real_amount_redis = _to_redis_int(real_amount["value"], real_amount["scale"])
        # delta is negative when real_cost < hold (typical case — over-estimated)
        delta = real_amount_redis - hold_amount_redis

        agg_key = self._AGG_KEY.format(project_id=project_id, period=billing_period)

        # Redis: adjust aggregate counter + delete hold in one pipeline.
        # Not strictly atomic across two keys, but the worst-case failure
        # (Redis blip between INCRBY and DELETE) only leaks the hold entry,
        # which expires via TTL anyway.
        async with self.redis.pipeline() as pipe:
            pipe.incrby(agg_key, delta)
            pipe.delete(hold_key)
            await pipe.execute()

        # Postgres: upsert MonthlyAggregate — always the source of truth.
        real_decimal = Decimal(real_amount["value"]) * Decimal(10) ** (
            -real_amount["scale"]
        )
        async with self.session_manager.get_session() as session:
            agg = await self.monthly_agg_repo.addToAggregate(
                session, project_id, billing_period, real_decimal
            )
            if agg is None:
                # Finalized period — should never happen in normal flow.
                self.logger.error(
                    "billing.release.finalized_aggregate",
                    hold_uuid=str(hold_uuid),
                    project_id=project_id,
                    billing_period=billing_period,
                )
            # TODO(BILL-008): INSERT BillingTransaction into TimescaleDB.
            await session.commit()

        self.logger.info(
            "billing.release.ok",
            hold_uuid=str(hold_uuid),
            project_id=project_id,
            billing_period=billing_period,
            real_amount_redis=real_amount_redis,
        )
        return Ok(True)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _effective_monthly_limit(
        self,
        session: AsyncSession,
        project_id: int,
        org_id: str,
    ) -> Decimal | None:
        """Return the tightest applicable monthly limit, or None (unlimited).

        Project-level limit takes precedence over org-level (per model docs).
        """
        proj = await self.project_limit_repo.getForProject(session, project_id)
        if proj is not None and proj.monthly_limit is not None:
            return proj.monthly_limit

        org = await self.org_limit_repo.getForOrg(session, org_id)
        if org is not None and org.monthly_limit is not None:
            return org.monthly_limit

        return None
