"""Repositories for Organization Postgres models."""

from src.db.repository import Repository

from .models import (
    OrgProject,
    OrgMetadata,
    OrgSettings,
    OrgInvitation,
    OrgDeletionRequest,
)

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class OrgMetadataRepository(Repository[OrgMetadata, str]):
    """Repository for persisted organization metadata."""

    def __init__(self):
        super().__init__(OrgMetadata, OrgMetadata.org_id)

    async def get(
        self, session: AsyncSession, org_id: str
    ) -> OrgMetadata | None:
        return await self.getByKey(session, org_id)

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        name: str,
        owner_id: str,
    ) -> OrgMetadata:
        metadata = await self.getByKey(session, org_id)
        if metadata is None:
            metadata = OrgMetadata(
                org_id=org_id,
                name=name,
                owner_id=owner_id,
            )
            session.add(metadata)
        else:
            metadata.name = name
            metadata.owner_id = owner_id
        await session.flush()
        await session.refresh(metadata)
        return metadata

    async def delete_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> bool:
        metadata = await self.getByKey(session, org_id)
        if metadata is None:
            return False
        await session.delete(metadata)
        await session.flush()
        return True


class OrgSettingsRepository(Repository[OrgSettings, str]):
    """Repository for OrgSettings (keyed by org_id)."""

    def __init__(self):
        super().__init__(OrgSettings, OrgSettings.org_id)

    async def get_or_create(
        self, session: AsyncSession, org_id: str
    ) -> OrgSettings:
        """Return existing settings or create default ones."""
        existing = await self.getByKey(session, org_id)
        if existing is not None:
            return existing
        new_settings = OrgSettings(org_id=org_id, extra={})
        session.add(new_settings)
        await session.flush()
        return new_settings

    async def upsert(
        self,
        session: AsyncSession,
        org_id: str,
        rate_limit: int | None,
        extra: dict,
    ) -> OrgSettings:
        """Create or update settings for an organization."""
        settings = await self.get_or_create(session, org_id)
        settings.rate_limit = rate_limit
        settings.extra = extra
        await session.flush()
        await session.refresh(settings)
        return settings


class OrgDeletionRequestRepository(Repository[OrgDeletionRequest, int]):
    """Repository for organization deletion requests."""

    def __init__(self):
        super().__init__(OrgDeletionRequest, OrgDeletionRequest.id)

    async def get_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> OrgDeletionRequest | None:
        stmt = (
            select(OrgDeletionRequest)
            .where(OrgDeletionRequest.org_id == org_id)
            .where(OrgDeletionRequest.cancelled.is_(False))
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def get_any_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> OrgDeletionRequest | None:
        stmt = (
            select(OrgDeletionRequest)
            .where(OrgDeletionRequest.org_id == org_id)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def create(
        self,
        session: AsyncSession,
        entity: OrgDeletionRequest,
    ) -> OrgDeletionRequest:
        session.add(entity)
        await session.flush()
        return entity

    async def upsert_request(
        self,
        session: AsyncSession,
        org_id: str,
        requested_by: str,
        cancel_before,
    ) -> OrgDeletionRequest:
        existing = await self.get_any_by_org_id(session, org_id)
        if existing is None:
            existing = OrgDeletionRequest(
                org_id=org_id,
                requested_by=requested_by,
                cancel_before=cancel_before,
                cancelled=False,
            )
            session.add(existing)
        else:
            existing.requested_by = requested_by
            existing.cancel_before = cancel_before
            existing.cancelled = False
        await session.flush()
        await session.refresh(existing)
        return existing

    async def list_due(
        self,
        session: AsyncSession,
        now,
        limit: int = 100,
    ) -> list[OrgDeletionRequest]:
        stmt = (
            select(OrgDeletionRequest)
            .where(OrgDeletionRequest.cancelled.is_(False))
            .where(OrgDeletionRequest.cancel_before <= now)
            .order_by(OrgDeletionRequest.cancel_before.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> bool:
        record = await self.get_by_org_id(session, org_id)
        if record is None:
            return False
        await session.delete(record)
        await session.flush()
        return True

    async def cancel_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> OrgDeletionRequest | None:
        record = await self.get_by_org_id(session, org_id)
        if record is None:
            return None
        record.cancelled = True
        await session.flush()
        await session.refresh(record)
        return record


class OrgProjectRepository(Repository[OrgProject, int]):
    """Repository for organisation projects."""

    def __init__(self):
        super().__init__(OrgProject, OrgProject.id)

    async def get_by_org_id(
        self,
        session: AsyncSession,
        org_id: str,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> list[OrgProject]:
        stmt = (
            select(OrgProject)
            .where(OrgProject.org_id == org_id)
            .order_by(OrgProject.id.desc())
            .offset(offset)
            .limit(limit)
        )
        if q:
            stmt = stmt.where(OrgProject.name.ilike(f"%{q}%"))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_org_id(self, session: AsyncSession, org_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(OrgProject)
            .where(OrgProject.org_id == org_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def create(
        self, session: AsyncSession, entity: OrgProject
    ) -> OrgProject:
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def delete_by_org_id(self, session: AsyncSession, org_id: str) -> int:
        stmt = select(OrgProject).where(OrgProject.org_id == org_id)
        result = await session.execute(stmt)
        projects = list(result.scalars().all())
        for project in projects:
            await session.delete(project)
        await session.flush()
        return len(projects)


class OrgInvitationRepository(Repository[OrgInvitation, int]):
    """Repository for invitation records with permissions."""

    def __init__(self):
        super().__init__(OrgInvitation, OrgInvitation.id)

    async def get_by_org_id(
        self, session: AsyncSession, org_id: str
    ) -> list[OrgInvitation]:
        stmt = (
            select(OrgInvitation)
            .where(OrgInvitation.org_id == org_id)
            .order_by(OrgInvitation.id.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_org_and_email(
        self, session: AsyncSession, org_id: str, email: str
    ) -> OrgInvitation | None:
        stmt = (
            select(OrgInvitation)
            .where(OrgInvitation.org_id == org_id)
            .where(OrgInvitation.email == email)
            .order_by(OrgInvitation.id.desc())
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def get_by_id_and_org(
        self, session: AsyncSession, invitation_id: int, org_id: str
    ) -> OrgInvitation | None:
        stmt = (
            select(OrgInvitation)
            .where(OrgInvitation.id == invitation_id)
            .where(OrgInvitation.org_id == org_id)
            .limit(1)
        )
        return await self.selectOne(session, stmt)

    async def create(
        self, session: AsyncSession, entity: OrgInvitation
    ) -> OrgInvitation:
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def delete_by_id_and_org(
        self, session: AsyncSession, invitation_id: int, org_id: str
    ) -> bool:
        inv = await self.get_by_id_and_org(session, invitation_id, org_id)
        if inv is None:
            return False
        await session.delete(inv)
        await session.flush()
        return True

    async def delete_by_org_and_email(
        self, session: AsyncSession, org_id: str, email: str
    ) -> bool:
        inv = await self.get_by_org_and_email(session, org_id, email)
        if inv is None:
            return False
        await session.delete(inv)
        await session.flush()
        return True

    async def upsert_by_org_email(
        self,
        session: AsyncSession,
        org_id: str,
        email: str,
        invited_by: str | None,
        permissions: list[str],
        status: str = "pending",
    ) -> OrgInvitation:
        inv = await self.get_by_org_and_email(session, org_id, email)
        if inv is None:
            inv = OrgInvitation(
                org_id=org_id,
                email=email,
                invited_by=invited_by,
                permissions=permissions,
                status=status,
            )
            session.add(inv)
        else:
            inv.invited_by = invited_by
            inv.permissions = permissions
            inv.status = status

        await session.flush()
        await session.refresh(inv)
        return inv

    async def delete_by_org_id(self, session: AsyncSession, org_id: str) -> int:
        invs = await self.get_by_org_id(session, org_id)
        for inv in invs:
            await session.delete(inv)
        await session.flush()
        return len(invs)
