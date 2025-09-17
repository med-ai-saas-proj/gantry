from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE
from src.services.ehr_summary import EHRSummaryService
from src.utils.logger import LOGGER
from src.services.crawler import CrawlerService
from src.agents import EHR_SUMMARY_AGENT
from src.consts.env import EnvConsts

CRAWLER_SERVICE = CrawlerService(
    CORE_DB_SESSION_SCOPE,
    LOGGER,
    EnvConsts.GOOGLE_PROGRAMMATIC_SEARCH_API_KEY,
    EnvConsts.GOOGLE_PROGRAMMATIC_SEARCH_CX,
)
EHR_SUMMARY_SERVICE = EHRSummaryService(
    CORE_DB_SESSION_SCOPE, LOGGER, EHR_SUMMARY_AGENT
)
