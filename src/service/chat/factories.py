from src.db.factories import getRedis, getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getChatAgent
from .services import ChatService
from ..utils.agent.factories import getModelsService
from ..utils.conversation.factories import getConversationService

from functools import lru_cache


@lru_cache(1)
def getChatService():
    """Returns a cached instance of the ChatService."""
    return ChatService(
        getSessionManager(),
        getLogger(),
        getChatAgent(),
        getModelsService(),
        getConversationService(),
        getRedis()
    )
