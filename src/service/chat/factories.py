from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getChatAgent
from .services import ChatService
from ..utils.agent.llms import AvailableModels, getModel

from functools import lru_cache


@lru_cache(1)
def getChatService():
    return ChatService(
        getSessionManager(),
        getLogger(),
        getChatAgent(
            getModel(AvailableModels.SmallModel).unwrap(),
        ),
    )
