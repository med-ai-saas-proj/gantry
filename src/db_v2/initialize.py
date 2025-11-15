from sqlalchemy.ext.asyncio import create_async_engine

from src.db_v2.consts import DB_ASYNC_URL
from src.db_v2.session import AsyncSessionManager

async_engine = create_async_engine(DB_ASYNC_URL, echo=True)

session_manager = AsyncSessionManager(async_engine)
