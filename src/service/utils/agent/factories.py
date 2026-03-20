from src.db.factories import getSessionManager
from src.shared.logging.logger import getLogger
from src.service.utils.models.settings import getModelsSettings
from src.service.utils.agent.prompt_service import PromptService
from src.service.utils.models.models_service import ModelsService

from functools import lru_cache


@lru_cache(1)
def getPromptService():
    """Returns a cached instance of the PromptService."""
    return PromptService(getSessionManager(), getLogger())


@lru_cache(1)
def getModelsService():
    """Returns a cached instance of the ModelsService."""
    return ModelsService(getModelsSettings(), getSessionManager(), getLogger())
