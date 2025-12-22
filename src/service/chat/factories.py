from src.shared.llms import small_model
from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import create_agent
from .services import ChatService

from functools import lru_cache


@lru_cache(1)
def getChatService():
    return ChatService(
        getSessionManager(), getLogger(), create_agent(small_model)
    )
