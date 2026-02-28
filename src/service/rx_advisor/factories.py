from src.db.factories import getSessionManager
from src.service.utils.conversation.factories import getConversationManager
from src.shared.utils.logger import getLogger

from .agents import getRxAdvisorAgent
from .services import RxAdvisorService
from ..utils.agent.factories import getModelsService

from functools import lru_cache


@lru_cache(1)
def getRxAdvisorService():
    """Returns a cached instance of the RxAdvisorService."""
    return RxAdvisorService(
        getSessionManager(),
        getLogger(),
        getRxAdvisorAgent(),
        getModelsService(),
        getConversationManager(),
    )
