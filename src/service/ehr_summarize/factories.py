from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getEhrSummarizeAgent
from .services import EHRSummarizeService
from ..utils.agent.llms import groq_small_model

from functools import lru_cache


@lru_cache(1)
def getEHRSummarizeService():
    return EHRSummarizeService(
        getSessionManager, getLogger(), getEhrSummarizeAgent(groq_small_model)
    )
