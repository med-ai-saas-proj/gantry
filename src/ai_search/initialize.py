from src.shared.utils.logger import LOGGER

from .agents import AI_SEARCH_AGENT
from .services import AISearchService


AI_SEARCH_SERVICE = AISearchService(LOGGER, AI_SEARCH_AGENT)
