from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE
from src.consts.env import EnvConsts
from src.utils.logger import LOGGER

from src.services.ehr_summary import EHRSummaryService
from src.services.rx_advisor import RxAdvisorService
from src.services.ai_search import AISearchService
from src.agents import EHR_SUMMARY_AGENT, RX_ADVISOR_AGENT, AI_SEARCH_AGENT
from src.services.api_key import ApiKeyServices
from src.services.user import UserService


EHR_SUMMARY_SERVICE = EHRSummaryService(
    CORE_DB_SESSION_SCOPE, LOGGER, EHR_SUMMARY_AGENT
)
RX_ADVISOR_SERVICE = RxAdvisorService(
    CORE_DB_SESSION_SCOPE, LOGGER, RX_ADVISOR_AGENT
)
AI_SEARCH_SERVICE = AISearchService(
    CORE_DB_SESSION_SCOPE, LOGGER, AI_SEARCH_AGENT
)

API_KEY_SERVICE = ApiKeyServices(CORE_DB_SESSION_SCOPE)
USER_SERVICE = UserService(CORE_DB_SESSION_SCOPE)
