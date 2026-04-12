"""Billing repository layer."""

from gantry.db.repository import Repository

from ..models import SpendingLimit, SpendingLimitType

from typing import Sequence
from decimal import Decimal

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


class SpendingLimitRepository(Repository[SpendingLimit, int]):
    """Repository forspending limits."""

    def __init__(self):
        super().__init__(SpendingLimit, SpendingLimit.id)

    async def get(
        self,
        session: AsyncSession,
        org_id: str,
        project_id: int,
        limit_type: SpendingLimitType,
    ) -> Sequence[SpendingLimit]:
        """Get the spending limit record for an organization."""
        stmt = select(SpendingLimit).where(
            (SpendingLimit.organization_id == org_id)
            & (
                (SpendingLimit.project_id == project_id)
                | SpendingLimit.project_id.is_(None)  # global default
            )
            & (SpendingLimit.limit_type == limit_type)
        )
        return await self.selectMany(session, stmt)

    async def getProjectLimits(
        self,
        session: AsyncSession,
        org_id: str,
        project_id: int,
        limit_type: SpendingLimitType,
    ) -> SpendingLimit | None:
        """Get the spending limit record for an organization."""
        stmt = select(SpendingLimit).where(
            (SpendingLimit.organization_id == org_id)
            & (SpendingLimit.project_id == project_id)
            & (SpendingLimit.limit_type == limit_type)
        )
        return await self.selectOne(session, stmt)

    async def getOrgLimits(
        self,
        session: AsyncSession,
        org_id: str,
        limit_type: SpendingLimitType,
    ) -> SpendingLimit | None:
        """Get the spending limit record for an organization."""
        stmt = select(SpendingLimit).where(
            (SpendingLimit.organization_id == org_id)
            & (SpendingLimit.project_id.is_(None))  # global default
            & (SpendingLimit.limit_type == limit_type)
        )
        return await self.selectOne(session, stmt)

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        project_id: int | None,
        monthly_limit: Decimal | None,
        daily_limit: Decimal | None,
    ) -> SpendingLimit | None:
        """Create or update the spending limits for an organization."""
        if project_id is not None:
            stmt = (
                insert(SpendingLimit)
                .values(
                    organization_id=org_id,
                    project_id=project_id,
                    monthly_limit=monthly_limit,
                    daily_limit=daily_limit,
                )
                .on_conflict_do_update(
                    index_elements=["organization_id", "project_id"],
                    set_={
                        "monthly_limit": monthly_limit,
                        "daily_limit": daily_limit,
                        "updated_at": func.now(),
                    },
                )
                .returning(SpendingLimit)
            )
        else:
            stmt = (
                insert(SpendingLimit)
                .values(
                    organization_id=org_id,
                    monthly_limit=monthly_limit,
                    daily_limit=daily_limit,
                )
                .on_conflict_do_update(
                    index_elements=["organization_id"],
                    index_where=SpendingLimit.project_id.is_(None),
                    set_={
                        "monthly_limit": monthly_limit,
                        "daily_limit": daily_limit,
                        "updated_at": func.now(),
                    },
                )
                .returning(SpendingLimit)
            )
        result = await session.execute(stmt)
        return result.scalars().first()
