from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE
from src.services.ehr_summary import EHRSummaryService
from src.utils.logger import LOGGER

from src.agents import EHR_SUMMARY_AGENT

EHR_SUMMARY_SERVICE = EHRSummaryService(
    CORE_DB_SESSION_SCOPE, LOGGER, EHR_SUMMARY_AGENT
)
