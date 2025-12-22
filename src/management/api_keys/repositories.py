"""API key repository."""

from src.db.repository import Repository

from .models import ApiKey, Permission

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionRepository(Repository[Permission, str]):
    """Permission repository."""

    def __init__(self):
        """Initialize PermissionRepository."""
        super().__init__(Permission, Permission.name)


class ApiKeyRepository(Repository[ApiKey, int]):
    """API key repository."""

    def __init__(self):
        """Initialize ApiKeyRepository."""
        super().__init__(ApiKey, ApiKey.id)

    async def getByHashedKey(self, session: AsyncSession, hashed_key: str):
        stmt = select(ApiKey).where(ApiKey.hashed_key == hashed_key).limit(1)
        stmt = self.buildOptions(
            stmt, load_relations={ApiKey.permissions: None}
        )
        return await self.selectOne(session, stmt)

    async def addApiKey(
        self,
        session: AsyncSession,
        user_id: str,
        hashed_key: str,
        hint: str,
        name: str,
        description: str,
        permissions: list[Permission],
    ):
        api_key = ApiKey(
            user_id=user_id,
            hashed_key=hashed_key,
            hint=hint,
            name=name,
            description=description,
            permissions=permissions,
        )
        session.add(api_key)
