from src.shared.llms import small_model
from src.shared.utils.logger import getLogger
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

from .agents import create_agent
from .services import ChatService

from functools import lru_cache


@lru_cache(1)
def getChatService():
    return ChatService(
        CORE_DB_SESSION_SCOPE, getLogger(), create_agent(small_model)
    )
