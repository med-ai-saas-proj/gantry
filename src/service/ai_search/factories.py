from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getAiSearchAgent
from .services import AiSearchService
from ..utils.agent.llms import GROQ_SMALL_MODEL, groq_small_model

from functools import lru_cache


@lru_cache(1)
def getAiSearchService():
    return AiSearchService(
        getSessionManager(), getLogger(), getAiSearchAgent(GROQ_SMALL_MODEL)
    )
