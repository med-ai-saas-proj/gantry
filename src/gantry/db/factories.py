"""Initialize database connections and session manager."""

from .session import AsyncSessionManager
from .settings import getDBSettings
from .repositories import RedisCacheRepository

from functools import lru_cache

from redis.asyncio import Redis, ConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


@lru_cache(1)
def getAsyncEngine():
    engine = create_async_engine(
        getDBSettings().timescale_connection_uri.encoded_string(), echo=False
    )
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    return engine


@lru_cache(1)
def getSessionManager():
    return AsyncSessionManager(getAsyncEngine())


@lru_cache(1)
def getRedisConnectionPool():
    return ConnectionPool.from_url(
        getDBSettings().redis_connection_uri.encoded_string(),
        decode_responses=False,
    )


@lru_cache(1)
def getRedisTextConnectionPool():
    return ConnectionPool.from_url(
        getDBSettings().redis_connection_uri.encoded_string(),
        decode_responses=True,
    )


@lru_cache(1)
def getRedis() -> Redis:
    return Redis(
        connection_pool=getRedisTextConnectionPool(),
    )


@lru_cache(1)
def getRedisBinary() -> Redis:
    return Redis(
        connection_pool=getRedisConnectionPool(),
        decode_responses=False,
    )


@lru_cache(1)
def getRedisCacheRepo() -> RedisCacheRepository:
    return RedisCacheRepository(
        getRedisBinary(),
        ttl=getDBSettings().cache_ttl,
    )
