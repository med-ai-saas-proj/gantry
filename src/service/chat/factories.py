from src.shared.utils.logger import getLogger
from src.shared.agents.agent_manager_factories import getAgentManager

from .services import ChatService

from functools import lru_cache


@lru_cache(1)
def getChatService():
    """Get ChatService singleton."""
    return ChatService(getLogger(), getAgentManager())
