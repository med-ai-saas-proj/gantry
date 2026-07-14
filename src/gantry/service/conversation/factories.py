from gantry.db.factories import getRedis, getSessionManager
from gantry.shared.logging.logger import getLogger

from .settings import getConversationSettings
from .repository import ConversationRepository
from .services.tree import TreeConversationService
from .services.sequence import (
    SequenceConversationService,
    SequenceConversationWithSerializerService,
)
from .conversation_manager import (
    ConversationManager,
)
from ..file_storage.factories import getFileStorageService
from .services.pydantic_ai_serializer import (
    PydanticAISerializer,
)

from functools import lru_cache


@lru_cache(1)
def getPydanticAISequenceConversationService():
    """Returns a cached instance of the ConversationService."""
    return SequenceConversationWithSerializerService(
        getSessionManager(),
        ConversationRepository(),
        getFileStorageService(),
        getRedis(),
        getConversationSettings(),
        PydanticAISerializer(getFileStorageService()),
    )


@lru_cache(1)
def getSequenceConversationService():
    """Returns a cached instance of the ConversationService."""
    return SequenceConversationService(
        getSessionManager(),
        ConversationRepository(),
        getFileStorageService(),
        getRedis(),
        getConversationSettings(),
    )


@lru_cache(1)
def getTreeConversationService():
    """Returns a cached instance of the ConversationService."""
    return TreeConversationService(
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
        getLogger(),
        getRedis(),
        getPydanticAISequenceConversationService(),
        getFileStorageService(),
    )
