from src.shared.utils.logger import LOGGER

from .services import RxAdvisorService
from ...shared.agents.factories import getAgentManager

from functools import lru_cache



@lru_cache(1)
def getRxAdvisorService() -> RxAdvisorService:
    agent_manager = getAgentManager()

    return RxAdvisorService(
        LOGGER,
        agent_manager,
    )