from src.db.factories import getSessionManager
from src.shared.logging.logger import getLogger

from .agents import getAiSearchAgent
from .services import AiSearchService
from ..utils.agent.factories import getModelsService

from functools import lru_cache


@lru_cache(1)
def getAiSearchService():
    """Returns a cached instance of the AiSearchService."""
    return AiSearchService(
        getSessionManager(), getLogger(), getAiSearchAgent(), getModelsService()
    )
