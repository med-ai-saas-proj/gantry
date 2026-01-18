from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger
from src.service.utils.agent.model_service import ModelService
from src.service.utils.agent.prompt_service import PromptService

from functools import lru_cache


@lru_cache(1)
def getPromptService():
    return PromptService(getSessionManager(), getLogger())


@lru_cache(1)
def getModelService():
    return ModelService()
