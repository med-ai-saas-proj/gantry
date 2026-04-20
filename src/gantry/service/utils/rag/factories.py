from gantry.db.factories import getSessionManager
from gantry.service.utils.rag.settings import getRagSettings
from gantry.management.project.repositories import ProjectRepository
from gantry.service.utils.file_storage.repositories import FileRepository

from .services import RagService

from functools import lru_cache


@lru_cache(1)
def getRagService():
    """Returns a cached instance of the RagService."""

    return RagService(
        getSessionManager(),
        ProjectRepository(),
        FileRepository(),
        getRagSettings(),
    )
