from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE
from src.consts.env import EnvConsts
from src.utils.logger import LOGGER

from src.services.crawler import CrawlerService


CRAWLER_SERVICE = CrawlerService(
    CORE_DB_SESSION_SCOPE,
    LOGGER,
    EnvConsts.GOOGLE_PROGRAMMATIC_SEARCH_API_KEY,
    EnvConsts.GOOGLE_PROGRAMMATIC_SEARCH_CX,
)
