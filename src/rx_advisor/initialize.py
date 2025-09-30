from src.shared.utils.logger import LOGGER
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

from .agents import RX_ADVISOR_AGENT
from .services import RxAdvisorService


RX_ADVISOR_SERVICE = RxAdvisorService(
    CORE_DB_SESSION_SCOPE, LOGGER, RX_ADVISOR_AGENT
)
