"""Asynchronous database sessions management."""

import contextlib

from sqlalchemy.ext.asyncio import AsyncSession


class AsyncSessionManager:
    """Asynchronous session manager for database interactions."""

    def __init__(self, async_engine):
        """Initialize the session manager with the given async engine."""
        self.async_engine = async_engine

    @contextlib.asynccontextmanager
    async def get_session(self):
        """Provide an asynchronous database session."""
        async with AsyncSession(self.async_engine) as session:
            try:
                yield session
                # manual commit in caller, because `return Error(...)`
                # in code can't roll back (it not raises an exception)
                # await session.commit()
            except Exception:
                await session.rollback()
                raise
