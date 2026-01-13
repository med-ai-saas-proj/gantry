from src.db.factories import getSessionManager
from src.shared.utils.logger import getLogger

from .agents import getRxAdvisorAgent
from .services import RxAdvisorService
from ..utils.agent.llms import small_model

from functools import lru_cache


lru_cache(1)


def getRxAdvisorService():
    return RxAdvisorService(
        getSessionManager(), getLogger(), getRxAdvisorAgent(small_model)
    )
