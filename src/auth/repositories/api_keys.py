"""API key repository."""

from src.db.repository import Repository
from src.auth.models.api_keys import ApiKeys, Permissions, ApiKeyPermissions

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


class PermissionRepository(Repository[Permissions, str]):
    """Permission repository."""

    def __init__(self):
        """Initialize PermissionRepository."""
        super().__init__(Permissions, Permissions.name)


class ApiKeyRepository(Repository[ApiKeys, uuid.UUID]):
    """API key repository."""

    def __init__(self):
        """Initialize ApiKeyRepository."""
        super().__init__(ApiKeys, ApiKeys.id)

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
