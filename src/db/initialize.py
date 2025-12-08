"""Initialize database connections and session manager."""

from src.db.session import AsyncSessionManager

from .settings import getDBSettings

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine


async_engine = create_async_engine(
    getDBSettings().postgres_connection_uri.encoded_string(), echo=True
)

session_manager = AsyncSessionManager(async_engine)

redis = Redis.from_url(getDBSettings().redis_connection_uri.encoded_string())
