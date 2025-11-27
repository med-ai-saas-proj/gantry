"""API key repository."""

from src.db_v2.repository import Repository
from src.auth.models.api_keys import ApiKey, Permission, ApiKeyPermissions

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionRepository(Repository):
    """Permission repository."""

    async def getPermissionByNames(
        self, session: AsyncSession, name_list: list[str]
    ) -> Sequence[Permission]:
        """Get permission by names."""
        return await self.selectMany(
            session, select(Permission).where(Permission.name.in_(name_list))
        )


class ApiKeyRepository(Repository):
    """API key repository."""

    async def addPermissionsToApiKey(
        self,
        session: AsyncSession,
        api_key_id: uuid.UUID,
        permissions: list[str],
    ):
        """Add permissions to API Key."""
        session.add_all(
            [
                ApiKeyPermissions(
                    api_key_id=api_key_id,
                    permission_name=permission,
                )
                for permission in permissions
            ]
        )

    async def getApiKeyById(
        self, session: AsyncSession, api_key_id: uuid.UUID
    ) -> ApiKey | None:
        """Get API key by its ID."""
        return await self.selectOne(
            session,
            select(ApiKey)
            .options(selectinload(ApiKey.permissions))
            .where(ApiKey.id == api_key_id)
            .limit(1),
        )
