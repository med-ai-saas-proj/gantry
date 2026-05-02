import asyncio
from contextlib import asynccontextmanager

from redis.asyncio.lock import Lock


class RedisAutoExtendAsyncLock:
    def __init__(self, lock: Lock) -> None:
        self.lock = lock
        self.task = None

    async def __aenter__(self):
        lock = await self.lock.__aenter__()

        async def auto_extend():
            if lock.timeout:
                try:
                    while True:
                        await asyncio.sleep(lock.timeout * 0.8)
                        lock.extend(lock.timeout)
                finally:
                    pass

        self.task = asyncio.create_task(auto_extend())
        return lock

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.task:
            self.task.cancel()
        return await self.lock.__aexit__(exc_type, exc_value, traceback)
