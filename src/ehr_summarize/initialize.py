from src.shared.utils.logger import LOGGER
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

from .agents import EHR_SUMMARY_AGENT
from .services import EHRSummaryService


EHR_SUMMARY_SERVICE = EHRSummaryService(
    CORE_DB_SESSION_SCOPE, LOGGER, EHR_SUMMARY_AGENT
)
