from gantry.db.session import AsyncSessionManager

import asyncio
from typing import Callable, Awaitable
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import LockNotOwnedError
from redis.asyncio.lock import Lock
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def redis_lock(
    redis_client: Redis,
    resource: str,
    lock_ttl: int = 10,
    blocking_timeout: float | None = None,
    retry_delay: float = 0.1,
    raise_on_timeout: bool = True,
):
    """Acquire a Redis lock for a given resource."""
    lock = redis_client.lock(
        resource,
        timeout=lock_ttl,
        blocking_timeout=blocking_timeout,
        sleep=retry_delay,
    )
    get_lock = await lock.acquire()
    if not get_lock:
        if raise_on_timeout:
            raise TimeoutError(
                f"Could not acquire lock for resource: {resource}"
            )
        else:
            yield None
            return
    service_task = asyncio.current_task()
    watchdog = asyncio.create_task(lock_watchdog(lock, lock_ttl, service_task))
    try:
        yield lock
    finally:
        watchdog.cancel()
        try:
            await watchdog
        except asyncio.CancelledError:
            pass  # Task was cancelled, which is expected when the lock is released
        await lock.release()


async def lock_watchdog(
    lock: Lock,
    ttl: int,
    service_task: asyncio.Task | None = None,
):
    """Background task to extend the lock TTL."""
    while True:
        try:
            await asyncio.sleep(ttl / 4)
            await lock.extend(ttl, replace_ttl=True)
        except LockNotOwnedError:
            if service_task and not service_task.done():
                service_task.cancel()
            break
        except Exception:
            continue  # likely a connection issue, will try again on next loop


async def redis_get_or_load[T](
    redis: Redis,
    session_manager: AsyncSessionManager,
    lock_id: str,
    lock_ttl: int,
    lock_blocking_timeout: int,
    getter: Callable[[Redis], Awaitable[T | None]],
    loader: Callable[[AsyncSession], Awaitable[T]],
    setter: Callable[[Redis, T], Awaitable[None]],
    retry_times: int = 3,
) -> T | None:
    """Helper to get a value from Redis or load it using the provided loader function."""
    for _ in range(retry_times):
        if v := await getter(redis):
            return v
        async with redis_lock(
            redis,
            f"billing:redis_get_or_load_lock:{lock_id}",
            lock_ttl=lock_ttl,
            blocking_timeout=lock_blocking_timeout,
        ) as lock_acquired:
            if not lock_acquired:
                # Failed to acquire lock, likely another process is loading the value. Wait and retry.
                await asyncio.sleep(0.2)
                continue

            # Double-check after acquiring the lock
            if v := await getter(redis):
                return v

            # Load the value using the provided loader function
            try:
                async with session_manager.get_session() as session:
                    loaded_value = await loader(session)
                    await setter(redis, loaded_value)
            except Exception as e:
                await asyncio.sleep(
                    0.2
                )  # Sleep before retrying on loader failure
                continue
            return loaded_value

    if v := await getter(redis):
        return v
    return None


async def redis_check_or_load[T](
    redis: Redis,
    session_manager: AsyncSessionManager,
    lock_id: str,
    lock_ttl: int,
    lock_blocking_timeout: int,
    checker: Callable[[Redis], Awaitable[bool]],
    loader: Callable[[AsyncSession], Awaitable[T]],
    setter: Callable[[Redis, T], Awaitable[None]],
    retry_times: int = 3,
) -> bool:
    """Helper to get a value from Redis or load it using the provided loader function."""
    for _ in range(retry_times):
        if await checker(redis):
            return True
        async with redis_lock(
            redis,
            f"billing:redis_get_or_load_lock:{lock_id}",
            lock_ttl=lock_ttl,
            blocking_timeout=lock_blocking_timeout,
        ) as lock_acquired:
            if not lock_acquired:
                # Failed to acquire lock, likely another process is loading the value. Wait and retry.
                await asyncio.sleep(0.2)
                continue

            # Double-check after acquiring the lock
            if await checker(redis):
                return True

            # Load the value using the provided loader function
            try:
                async with session_manager.get_session() as session:
                    loaded_value = await loader(session)
                    await setter(redis, loaded_value)
            except Exception as e:
                await asyncio.sleep(
                    0.2
                )  # Sleep before retrying on loader failure
                continue
            return True

    return bool(await checker(redis))
