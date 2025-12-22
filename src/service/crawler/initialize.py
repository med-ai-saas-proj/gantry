from functools import lru_cache
from src.shared.utils.logger import LOGGER

from . import consts
from .services import CrawlerService


@lru_cache(1)
def getCrawlerService() -> CrawlerService:
    return CrawlerService(
        LOGGER,
        consts.GOOGLE_PROGRAMMATIC_SEARCH_API_KEY,
        consts.GOOGLE_PROGRAMMATIC_SEARCH_CX,
        max_concurrent_crawler=consts.CRAWLER_MAX_CONCURRENT,
    )
