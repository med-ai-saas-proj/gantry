from gantry.service.conversation import getTreeConversationService

from .services import AiGatewayService
from .settings import getAIGatewaySettings

from functools import lru_cache


@lru_cache(1)
def getAiGatewayService():
    return AiGatewayService(
        getAIGatewaySettings(), getTreeConversationService()
    )
