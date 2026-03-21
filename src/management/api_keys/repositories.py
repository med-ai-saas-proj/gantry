"""API key repository."""

from src.db.repository import Repository

from .models import ApiKey, Permission

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionRepository(Repository[Permission, str]):
    """Permission repository."""

    def __init__(self):
        """Initialize PermissionRepository."""
        super().__init__(Permission, Permission.name)

    async def getAllPermissions(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[Permission]:
        """Get all permissions with pagination."""
        stmt = (
            select(Permission)
            .offset(skip)
            .limit(limit)
            .order_by(Permission.name)
        )
        return await self.selectMany(session, stmt)

    async def countPermissions(self, session: AsyncSession) -> int:
        """Count total number of permissions."""
        stmt = select(func.count()).select_from(Permission)
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def getPermissionById(
        self, session: AsyncSession, permission_id: int
    ) -> Permission | None:
        """Get permission by ID."""
        stmt = select(Permission).where(Permission.id == permission_id).limit(1)
        return await self.selectOne(session, stmt)

    async def getPermissionByName(
        self, session: AsyncSession, name: str
    ) -> Permission | None:
        """Get permission by name."""
        stmt = select(Permission).where(Permission.name == name).limit(1)
        return await self.selectOne(session, stmt)

    async def createPermission(
        self, session: AsyncSession, name: str, description: str
    ) -> Permission:
        """Create a new permission."""
        permission = Permission(name=name, description=description)
        session.add(permission)
        await session.flush()
        return permission

    async def updatePermission(
        self, session: AsyncSession, permission: Permission, description: str
    ) -> Permission:
        """Update a permission's description."""
        permission.description = description
        await session.flush()
        await session.refresh(permission)
        return permission

    async def deletePermission(
        self, session: AsyncSession, permission: Permission
    ) -> None:
        """Delete a permission."""
        await self.delete(session, permission)


class ApiKeyRepository(Repository[ApiKey, int]):
    """API key repository."""

    def __init__(self):
        """Initialize ApiKeyRepository."""
        super().__init__(ApiKey, ApiKey.id)

    async def getByHashedKey(
        self, session: AsyncSession, hashed_key: str
    ) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.hashed_key == hashed_key).limit(1)
        stmt = self.buildOptions(
            stmt, load_relations={ApiKey.permissions: None}
        )
        return await self.selectOne(session, stmt)

    async def getByHashedKeys(
        self, session: AsyncSession, hashed_keys: list[str]
    ) -> Sequence[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.hashed_key.in_(hashed_keys))
        return await self.selectMany(session, stmt)

    async def getByUserId(
        self, session: AsyncSession, user_id: str
    ) -> Sequence[ApiKey]:
        """Get all API keys for a specific user."""
        stmt = select(ApiKey).where(ApiKey.user_id == user_id)
        stmt = self.buildOptions(
            stmt, load_relations={ApiKey.permissions: None}
        )
        return await self.selectMany(session, stmt)

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
