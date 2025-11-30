"""User repository."""

from src.db_v2.repository import ColumnList, Repository, RelationLoadMap
from src.auth.models.users import User

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository(Repository[User, uuid.UUID]):
    """User repository."""

    def __init__(self) -> None:
        """Initialize UserRepository."""
        super().__init__(User, User.id)

    async def getByUsernameOrEmail(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
    ) -> User | None:
        """Get user by username or email."""
        stmt = (
            select(User)
            .where((User.username == username) | (User.email == email))
            .limit(1)
        )
        stmt = self.buildOptions(
            stmt,
            load_columns,
            load_relations,
        )
        return await self.selectOne(
            session,
            stmt,
        )

    async def getByEmail(
        self,
        session: AsyncSession,
        email: str,
        load_columns: ColumnList = None,
        load_relations: RelationLoadMap = None,
    ) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email).limit(1)
        stmt = self.buildOptions(
            stmt,
            load_columns,
            load_relations,
        )
        return await self.selectOne(session, stmt)
