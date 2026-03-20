from src.db.factories import getSessionManager
from src.shared.logging.logger import getLogger
from src.service.utils.conversation.factories import getConversationManager

from .agents import getEhrSummarizeAgent
from .services import EHRSummarizeService
from ..utils.agent.factories import getModelsService

from functools import lru_cache


@lru_cache(1)
def getEHRSummarizeService():
    """Returns a cached instance of the EHRSummarizeService."""
    return EHRSummarizeService(
        getSessionManager,
        getLogger(),
        getEhrSummarizeAgent(),
        getModelsService(),
        getConversationManager(),
    )
