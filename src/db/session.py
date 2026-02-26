"""Asynchronous database sessions management."""

import contextlib

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class AsyncSessionManager:
    """Asynchronous session manager for database interactions."""

    def __init__(self, async_engine):
        """Initialize the session manager with the given async engine."""
        self.async_engine = async_engine
        self.sessionmaker = async_sessionmaker(async_engine, expire_on_commit=False)

    @contextlib.asynccontextmanager
    async def get_session(self):
        """Provide an asynchronous database session."""
        async with self.sessionmaker() as session:
            try:
                yield session
                # manual commit in caller, because `return Error(...)`
                # in code can't roll back (it not raises an exception)
                # await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.rollback()
