from src.shared.utils.logger import LOGGER
from src.shared.agents.factories import getAgentManager

from .services import EHRSummaryService

from functools import lru_cache


@lru_cache(1)
def getEhrSummaryService() -> EHRSummaryService:
    agent_manager = getAgentManager()
    return EHRSummaryService(LOGGER, agent_manager)