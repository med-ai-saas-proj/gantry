import asyncio
from functools import lru_cache

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler


@lru_cache(1)
def get_scheduler():
    return AsyncIOScheduler()


def add_cron_job(cron_expression: str, job_func):
    scheduler = get_scheduler()
    scheduler.add_job(job_func, CronTrigger.from_crontab(cron_expression))


async def main():
    scheduler = get_scheduler()
    scheduler.start()
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
