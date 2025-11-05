import contextlib

from sqlalchemy.ext.asyncio import AsyncSession


class AsyncSessionManager:
    def __init__(self, async_engine):
        self.async_engine = async_engine

    @contextlib.asynccontextmanager
    async def get_session(self):
        async with AsyncSession(self.async_engine) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
