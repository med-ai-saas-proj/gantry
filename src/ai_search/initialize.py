from src.shared.utils.logger import LOGGER
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

from .agents import AI_SEARCH_AGENT
from .services import AISearchService


AI_SEARCH_SERVICE = AISearchService(
    CORE_DB_SESSION_SCOPE, LOGGER, AI_SEARCH_AGENT
)
