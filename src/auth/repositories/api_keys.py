"""API key repository."""

from src.db_v2.repository import Repository
from src.auth.models.api_keys import ApiKey, Permission, ApiKeyPermissions

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


class PermissionRepository(Repository[Permission, str]):
    """Permission repository."""

    def __init__(self):
        """Initialize PermissionRepository."""
        super().__init__(Permission, Permission.name)


class ApiKeyRepository(Repository[ApiKey, uuid.UUID]):
    """API key repository."""

    def __init__(self):
        """Initialize ApiKeyRepository."""
        super().__init__(ApiKey, ApiKey.id)

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
