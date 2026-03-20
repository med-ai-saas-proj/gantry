"""Initialize database connections and session manager."""

from src.db.session import AsyncSessionManager

from .settings import getDBSettings

from functools import lru_cache

import aioredlock
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


def getAsyncEngine():
    engine = create_async_engine(
        getDBSettings().postgres_connection_uri.encoded_string(), echo=True
    )
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    return engine


@lru_cache(1)
def getSessionManager():
    return AsyncSessionManager(getAsyncEngine())


def getTimescaleAsyncEngine():
    engine = create_async_engine(
        getDBSettings().timescale_connection_uri.encoded_string(), echo=True
    )
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    return engine


@lru_cache(1)
def getTimescaleSessionManager():
    return AsyncSessionManager(getTimescaleAsyncEngine())


@lru_cache(1)
def getRedis() -> Redis:
    return Redis.from_url(getDBSettings().redis_connection_uri.encoded_string())


@lru_cache(1)
def getRedisLockManager():
    return aioredlock.Aioredlock(
        [getDBSettings().redis_connection_uri.encoded_string()]
    )
