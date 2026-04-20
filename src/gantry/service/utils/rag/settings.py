from gantry.settings import AppSettings
from gantry.settings.rag import RagSettings

from functools import lru_cache


@lru_cache(1)
def getRagSettings() -> RagSettings:
    """Returns a cached instance of RagSettings."""
    return AppSettings.get().rag
