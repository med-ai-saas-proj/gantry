from src.shared.utils.logger import LOGGER

from .agents import RX_ADVISOR_AGENT
from .services import RxAdvisorService


RX_ADVISOR_SERVICE = RxAdvisorService(LOGGER, RX_ADVISOR_AGENT)
