from src.shared.utils.logger import LOGGER
from src.shared.agents.agent_manager_factories import getAgentManager

from .services import EHRSummaryService

from functools import lru_cache


@lru_cache(1)
def getEhrSummaryService() -> EHRSummaryService:
    return EHRSummaryService(LOGGER, getAgentManager())
