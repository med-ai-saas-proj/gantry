from functools import lru_cache

from src.db.factories import getSessionManager
from src.service.utils.agent.model_service import ModelService
from src.service.utils.agent.prompt_service import PromptService
from src.shared.utils.logger import getLogger


@lru_cache(1)
def getPromptService():
    return PromptService(getSessionManager(), getLogger())


@lru_cache(1)
def getModelService():
    return ModelService()
