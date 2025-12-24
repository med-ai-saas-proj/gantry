from src.shared.utils.logger import LOGGER

from .services import RxAdvisorService
from ...shared.agents.agent_manager_factories import getAgentManager

from functools import lru_cache


@lru_cache(1)
def getRxAdvisorService() -> RxAdvisorService:
    return RxAdvisorService(
        LOGGER,
        getAgentManager(),
    )
