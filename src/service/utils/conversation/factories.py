from src.db.factories import getRedis, getSessionManager, getRedisLockManager
from src.service.utils.file_storage.factories import getFileStorageService

from .services import ConversationService
from .settings import getConversationSettings
from .repository import ConversationRepository
from .conversation_manager import (
    ConversationManager,
)

from functools import lru_cache


@lru_cache(1)
def getConversationService():
    """Returns a cached instance of the ConversationService."""
    return ConversationService(
        getSessionManager(),
        ConversationRepository(),
        getFileStorageService(),
        getRedis(),
        getConversationSettings(),
    )


@lru_cache(1)
def getConversationManager():
    """Returns a cached instance of the ConversationManager."""
    return ConversationManager(
        getConversationService(), getRedisLockManager(), getFileStorageService()
    )
