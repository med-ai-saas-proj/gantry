from src.shared.utils.logger import LOGGER
from src.shared.agents.agent_manager_factories import getAgentManager

from .services import AISearchService

from functools import lru_cache


@lru_cache(1)
def getAISearchService() -> AISearchService:
    """Get AI Search Service singleton."""
    return AISearchService(LOGGER, getAgentManager())
