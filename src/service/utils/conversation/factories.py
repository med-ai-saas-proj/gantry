from src.db.factories import getRedis, getSessionManager
from src.service.utils.conversation.services import ConversationService
from src.service.utils.file_storage.factories import getFileStorageService
from src.service.utils.conversation.repository import ConversationRepository

from functools import lru_cache


@lru_cache(1)
def getConversationService():
    """Returns a cached instance of the ConversationService."""
    return ConversationService(
        getSessionManager(),
        ConversationRepository(),
        getFileStorageService(),
        getRedis()
    )