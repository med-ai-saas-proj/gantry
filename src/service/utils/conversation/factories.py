from functools import lru_cache

from src.db.factories import getRedis, getSessionManager
from src.service.utils.conversation.repository import ConversationRepository
from src.service.utils.conversation.services import ConversationService


@lru_cache(1)
def getConversationService():
    """Returns a cached instance of the ConversationService."""
    return ConversationService(
        getSessionManager(),
        ConversationRepository(),
        getRedis()
    )