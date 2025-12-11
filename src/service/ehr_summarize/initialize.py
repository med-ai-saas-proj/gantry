from src.shared.utils.logger import LOGGER

from .agents import EHR_SUMMARY_AGENT
from .services import EHRSummaryService


EHR_SUMMARY_SERVICE = EHRSummaryService(LOGGER, EHR_SUMMARY_AGENT)
