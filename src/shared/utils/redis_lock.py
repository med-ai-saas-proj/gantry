import asyncio
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import LockNotOwnedError
from redis.asyncio.lock import Lock


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
