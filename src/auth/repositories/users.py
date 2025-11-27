from src.db_v2.repository import Repository
from src.auth.models.users import User

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository(Repository[User, uuid.UUID]):
    model = User
    key = User.id

    async def getByUsernameOrEmail(
        self, session: AsyncSession, username: str, email: str
    ) -> User | None:
        """Get user by username or email."""
        return await self.selectOne(
            session,
            select(User)
            .where((User.username == username) | (User.email == email))
            .limit(1),
        )

    async def getByEmail(
        self, session: AsyncSession, email: str
    ) -> User | None:
        """Get user by email."""
        return await self.selectOne(
            session, select(User).where(User.email == email).limit(1)
        )
