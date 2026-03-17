from src.db.factories import getSessionManager
from src.shared.logging.logger import getLogger

from .agents import getEhrSummarizeAgent
from .services import EHRSummarizeService
from ..utils.agent.llms import AvailableModels, getModel

from functools import lru_cache


lru_cache(1)


def getEHRSummarizeService():
    return EHRSummarizeService(
        getSessionManager,
        getLogger(),
        getEhrSummarizeAgent(
            getModel(AvailableModels.SmallModel).unwrap(),
        ),
    )
