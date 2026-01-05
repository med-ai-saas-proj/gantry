from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getAiSearchAgent
from .services import AiSearchService
from ..utils.agent.llms import small_model

from functools import lru_cache


@lru_cache(1)
def getAiSearchService():
    return AiSearchService(
        getSessionManager(), getLogger(), getAiSearchAgent(small_model)
    )
