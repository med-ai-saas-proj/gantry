from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getEhrSummarizeAgent
from .services import EHRSummarizeService

from functools import lru_cache

from ..utils.agent.factories import getModelsService


@lru_cache(1)
def getEHRSummarizeService():
    """Returns a cached instance of the EHRSummarizeService."""
    return EHRSummarizeService(
        getSessionManager,
        getLogger(),
        getEhrSummarizeAgent(),
        getModelsService(),
    )
