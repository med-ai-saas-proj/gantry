from src.shared.logging.logger import getLogger

from . import consts
from .services import CrawlerService


CRAWLER_SERVICE = CrawlerService(
    getLogger(),
    consts.GOOGLE_PROGRAMMATIC_SEARCH_API_KEY,
    consts.GOOGLE_PROGRAMMATIC_SEARCH_CX,
    max_concurrent_crawler=consts.CRAWLER_MAX_CONCURRENT,
)
