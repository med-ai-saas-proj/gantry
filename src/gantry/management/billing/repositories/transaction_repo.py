from gantry.db import Repository
from gantry.management.project.models import Project

from ..type import (
    AggregatePeriod,
    BillingAggregateReport,
    BillingTransactionInfo,
    BillingAggregateReportGroupedByProject,
    BillingAggregateReportGroupedByServiceAndProject,
)
from ..models import (
    TransactionStatus,
    BillingTransaction,
    TimescaleDBDailyBillingSummary,
)

from uuid import UUID
from typing import Sequence
from decimal import Decimal
from datetime import datetime

from sqlalchemy import and_, func, text, select, update
from sqlalchemy.ext.asyncio import AsyncSession


bucket_map = {
    AggregatePeriod.DAILY: "day",
    AggregatePeriod.WEEKLY: "week",
    AggregatePeriod.MONTHLY: "month",
    AggregatePeriod.YEARLY: "year",
}


class TransactionRepository(Repository[BillingTransaction, UUID]):
    """Repository for BillingTransaction records.

    BillingTransaction stores only apikey_id. For project/org-level queries
    the service layer resolves project_id / org_id -> apikey_ids first, then
    passes the list to getByApiKeys / sumByApiKeysInPeriod.
    """

    def __init__(self):
        super().__init__(BillingTransaction, BillingTransaction.uuid)

    async def addTransaction(
        self,
        session: AsyncSession,
        transaction_uid: UUID,
        apikey_id: int,
        project_id: int,
        org_id: str,
        amount: Decimal,
        details: dict,
        created_at: datetime,
        service_name: str,
        capture: bool = False,
    ) -> BillingTransaction:
        """Persist the final charge record (called during RELEASE)."""
        tx = BillingTransaction(
            uuid=transaction_uid,
            apikey_id=apikey_id,
            project_id=project_id,
            organization_id=org_id,
            amount=amount,
            details=details,
            captured_at=func.now() if capture else None,
            created_at=created_at,
            service_name=service_name,
            status=TransactionStatus.CAPTURED
            if capture
            else TransactionStatus.PENDING,
        )
        await self.add(session, tx)
        return tx

    async def getTransactionByUUID(
        self,
        session: AsyncSession,
        transaction_uid: UUID,
    ) -> BillingTransaction | None:
        """Get the transaction record by its UUID."""
        stmt = select(BillingTransaction).where(
            BillingTransaction.uuid == transaction_uid
        )
        return await self.selectOne(session, stmt)

    async def setTransactionsExpired(
        self,
        session: AsyncSession,
        expiration_time: datetime,
    ) -> Sequence[BillingTransaction]:
        """Set transactions that are pending for too long to expired."""
        stmt = (
            update(BillingTransaction)
            .where(
                BillingTransaction.captured_at.is_(None),
                BillingTransaction.created_at < expiration_time,
                BillingTransaction.status == TransactionStatus.PENDING,
            )
            .values(status=TransactionStatus.EXPIRED)
            .returning(BillingTransaction)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def captureTransaction(
        self,
        session: AsyncSession,
        transaction_uid: UUID,
        real_amount: Decimal,
    ) -> BillingTransaction | None:
        """Update the transaction record with the real amount and mark as captured (called during CAPTURE)."""
        stmt = (
            update(BillingTransaction)
            .where(
                (BillingTransaction.uuid == transaction_uid)
                & (BillingTransaction.captured_at.is_(None))
                & (BillingTransaction.status == TransactionStatus.PENDING)
            )
            .values(
                amount=real_amount,  # update to real amount
                captured_at=func.now(),
                status=TransactionStatus.CAPTURED,
            )
            .returning(BillingTransaction)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def getTransactionInfoList(
        self,
        session: AsyncSession,
        org_id: str,
        project_uuids: list[UUID] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[BillingTransactionInfo], int]:
        """Get the transaction records by a list of UUIDs."""
        stmt = (
            select(
                BillingTransaction.uuid,
                BillingTransaction.amount,
                BillingTransaction.created_at,
                BillingTransaction.details,
                BillingTransaction.captured_at,
                BillingTransaction.organization_id,
                BillingTransaction.status,
                BillingTransaction.service_name,
                Project.uuid.label("project_uuid"),
                func.count().over().label("total"),
            )
            .select_from(BillingTransaction)
            .join(Project, BillingTransaction.project_id == Project.id)
            .where(BillingTransaction.organization_id == org_id)
        )
        if project_uuids and len(project_uuids) > 0:
            stmt = stmt.where(Project.uuid.in_(project_uuids))
        if start_date:
            stmt = stmt.where(BillingTransaction.created_at >= start_date)
        if end_date:
            stmt = stmt.where(BillingTransaction.created_at <= end_date)
        stmt = stmt.order_by(BillingTransaction.created_at.desc())
        stmt = self.buildFilterPagination(stmt, offset=offset, limit=limit)
        res = await session.execute(stmt)
        rows = res.all()
        return [
            {
                "organization_id": row.organization_id,
                "transaction_uid": row.uuid,
                "amount": row.amount,
                "date": row.created_at,
                "project_uuid": row.project_uuid,
                "details": row.details,
                "captured_at": row.captured_at,
                "status": row.status,
                "service_name": row.service_name,
            }
            for row in rows
        ], rows[0].total if rows else 0

    async def getTransactionInfoByUUID(
        self,
        session: AsyncSession,
        transaction_uid: UUID,
        org_id: str,
    ) -> BillingTransactionInfo | None:
        """Get the transaction record by its UUID."""
        stmt = (
            select(
                BillingTransaction.uuid,
                BillingTransaction.amount,
                BillingTransaction.created_at,
                BillingTransaction.details,
                BillingTransaction.captured_at,
                BillingTransaction.organization_id,
                BillingTransaction.status,
                BillingTransaction.service_name,
                Project.uuid.label("project_uuid"),
            )
            .select_from(BillingTransaction)
            .join(Project, BillingTransaction.project_id == Project.id)
            .where(
                and_(
                    BillingTransaction.uuid == transaction_uid,
                    BillingTransaction.organization_id == org_id,
                )
            )
        )
        res = await session.execute(stmt)
        row = res.one_or_none()
        if not row:
            return None
        return {
            "organization_id": row.organization_id,
            "transaction_uid": row.uuid,
            "amount": row.amount,
            "date": row.created_at,
            "project_uuid": row.project_uuid,
            "details": row.details,
            "captured_at": row.captured_at,
            "status": row.status,
            "service_name": row.service_name,
        }

    async def getTransactionInfoByUUIDForAdmin(
        self,
        session: AsyncSession,
        transaction_uid: UUID,
    ) -> BillingTransactionInfo | None:
        """Get the transaction record by its UUID."""
        stmt = (
            select(
                BillingTransaction.uuid,
                BillingTransaction.amount,
                BillingTransaction.created_at,
                BillingTransaction.details,
                BillingTransaction.captured_at,
                BillingTransaction.organization_id,
                BillingTransaction.status,
                BillingTransaction.service_name,
                Project.uuid.label("project_uuid"),
            )
            .select_from(BillingTransaction)
            .join(Project, BillingTransaction.project_id == Project.id)
            .where(BillingTransaction.uuid == transaction_uid)
        )
        res = await session.execute(stmt)
        row = res.one_or_none()
        if not row:
            return None
        return {
            "organization_id": row.organization_id,
            "transaction_uid": row.uuid,
            "amount": row.amount,
            "date": row.created_at,
            "project_uuid": row.project_uuid,
            "details": row.details,
            "captured_at": row.captured_at,
            "status": row.status,
            "service_name": row.service_name,
        }

    async def getByApiKeys(
        self,
        session: AsyncSession,
        apikey_ids: list[int],
        org_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for a list of API keys, newest first."""
        if len(apikey_ids) == 0:
            return []  # no apikeys, no transactions
        stmt = (
            select(BillingTransaction)
            .where(
                and_(
                    BillingTransaction.apikey_id.in_(apikey_ids),
                    BillingTransaction.organization_id == org_id,
                )
            )
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def getByOrganizations(
        self,
        session: AsyncSession,
        org_ids: list[str],
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for an organization, newest first."""
        if len(org_ids) == 0:
            return []  # no orgs, no transactions
        stmt = (
            select(BillingTransaction)
            .where(BillingTransaction.organization_id.in_(org_ids))
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def getByProjects(
        self,
        session: AsyncSession,
        project_ids: list[int],
        org_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[BillingTransaction]:
        """Get transactions for a project, newest first."""
        if len(project_ids) == 0:
            return []  # no projects, no transactions
        stmt = (
            select(BillingTransaction)
            .where(
                and_(
                    BillingTransaction.project_id.in_(project_ids),
                    BillingTransaction.organization_id == org_id,
                )
            )
            .order_by(BillingTransaction.created_at.desc())
        )
        stmt = self.buildFilterPagination(stmt, offset=skip, limit=limit)
        return await self.selectMany(session, stmt)

    async def sumByPeriodFilterByOrganizations(
        self,
        session: AsyncSession,
        org_ids: list[str],
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,  # e.g. for period=weekly, period_scale=2 means 2-week aggregation buckets.
    ) -> Sequence[BillingAggregateReport]:
        """Sum the total amount for an organization in a time period."""
        if len(org_ids) == 0:
            return []  # no orgs, no data
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.organization_id.in_(org_ids),
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket)

        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]

    async def sumByPeriodFilterByProjects(
        self,
        session: AsyncSession,
        project_ids: list[int] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,  # e.g. for period=weekly, period_scale=2 means 2-week aggregation buckets.
    ) -> Sequence[BillingAggregateReport]:
        """Sum the total amount for a project in a time period."""
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.organization_id == org_id,
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if project_ids is not None and len(project_ids) > 0:
            stmt = stmt.where(
                TimescaleDBDailyBillingSummary.project_id.in_(project_ids)
            )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket)
        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]

    async def sumByPeriodGroupedByProjects(
        self,
        session: AsyncSession,
        project_ids: list[int] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,  # e.g. for period=weekly, period_scale=2 means 2-week aggregation buckets.
    ) -> Sequence[BillingAggregateReportGroupedByProject]:
        """Sum the total amount for a project in a time period."""
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            TimescaleDBDailyBillingSummary.project_id,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.organization_id == org_id,
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if project_ids is not None and len(project_ids) > 0:
            stmt = stmt.where(
                TimescaleDBDailyBillingSummary.project_id.in_(project_ids)
            )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket, TimescaleDBDailyBillingSummary.project_id)
        outer_stmt = select(
            stmt.c.period_bucket,
            stmt.c.transaction_count,
            stmt.c.total_amount,
            stmt.c.project_id,
            Project.name.label("group_by_name"),
            Project.uuid.label("group_by_key"),
        ).join(
            Project,
            stmt.c.project_id == Project.id,
        )

        result = await session.execute(outer_stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
                "project_int": row.project_id,
                "project_uuid": row.group_by_key,
                "project_name": row.group_by_name,
            }
            for row in rows
        ]

    async def sumByPeriodFilterByServiceName(
        self,
        session: AsyncSession,
        service_names: list[str],
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,
    ) -> Sequence[BillingAggregateReport]:
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        stmt = select(
            bucket,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.organization_id == org_id,
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if len(service_names) > 0:
            stmt = stmt.where(
                TimescaleDBDailyBillingSummary.service_name.in_(service_names)
            )
        if end_time:
            stmt = stmt.where(TimescaleDBDailyBillingSummary.bucket < end_time)
        stmt = stmt.group_by(bucket)

        result = await session.execute(stmt)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]

    async def sumByPeriodByServiceAndProjectGroupedByServiceAndProject(
        self,
        session: AsyncSession,
        service_names: list[str] | None,
        project_ids: list[int] | None,
        org_id: str,
        start_time: datetime,
        end_time: datetime | None,
        period: AggregatePeriod,
        period_scale: int = 1,
    ) -> Sequence[BillingAggregateReportGroupedByServiceAndProject]:
        bucket = func.public.time_bucket(
            text(f"'{period_scale} {bucket_map[period]}'"),
            TimescaleDBDailyBillingSummary.bucket,
        ).label("period_bucket")
        inner = select(
            bucket,
            TimescaleDBDailyBillingSummary.service_name,
            TimescaleDBDailyBillingSummary.project_id,
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.transaction_count),
                0,
            ).label("transaction_count"),
            func.coalesce(
                func.sum(TimescaleDBDailyBillingSummary.total_amount),
                Decimal("0"),
            ).label("total_amount"),
        ).where(
            TimescaleDBDailyBillingSummary.organization_id == org_id,
            TimescaleDBDailyBillingSummary.bucket >= start_time,
        )
        if service_names is not None and len(service_names) > 0:
            inner = inner.where(
                TimescaleDBDailyBillingSummary.service_name.in_(service_names)
            )
        if project_ids is not None and len(project_ids) > 0:
            inner = inner.where(
                TimescaleDBDailyBillingSummary.project_id.in_(project_ids)
            )
        if end_time:
            inner = inner.where(
                TimescaleDBDailyBillingSummary.bucket < end_time
            )
        inner = inner.group_by(
            bucket,
            TimescaleDBDailyBillingSummary.service_name,
            TimescaleDBDailyBillingSummary.project_id,
        )

        outer = select(
            inner.c.period_bucket,
            inner.c.service_name,
            inner.c.transaction_count,
            inner.c.total_amount,
            inner.c.project_id,
            Project.uuid.label("project_uuid"),
            Project.name.label("project_name"),
        ).join(
            Project,
            inner.c.project_id == Project.id,
        )

        result = await session.execute(outer)
        rows = result.all()
        return [
            {
                "period_bucket": row.period_bucket,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
                "service_name": row.service_name,
                "project_id": row.project_id,
                "project_uuid": row.project_uuid,
                "project_name": row.project_name,
            }
            for row in rows
        ]

    async def havePendingTransactionsForOrgInPeriod(
        self,
        session: AsyncSession,
        org_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        stmt = select(BillingTransaction.uuid).where(
            BillingTransaction.organization_id == org_id,
            BillingTransaction.status == TransactionStatus.PENDING,
            BillingTransaction.created_at >= start_time,
            BillingTransaction.created_at < end_time,
        )
        res = await session.execute(stmt)
        rows = res.all()
        return len(rows) > 0
