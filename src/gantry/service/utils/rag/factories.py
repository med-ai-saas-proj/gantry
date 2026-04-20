from gantry.db.factories import getRedis, getSessionManager
from gantry.shared.logging.logger import getLogger
from gantry.service.utils.rag.settings import getRagSettings
from gantry.management.project.repositories import ProjectRepository
from gantry.service.utils.file_storage.factories import getFileStorageService
from gantry.service.utils.file_storage.repositories import FileRepository

from .services import RagService

from functools import lru_cache

from openai import AsyncOpenAI


@lru_cache(1)
def getRagService():
    """Returns a cached instance of the RagService."""

    return RagService(
        getSessionManager(),
        ProjectRepository(),
        FileRepository(),
        getRagSettings(),
        getFileStorageService(),
        AsyncOpenAI(
            api_key=getRagSettings().openai_api_key.get_secret_value(),
            base_url=getRagSettings().openai_base_url,
        )
        if getRagSettings().openai_base_url
        else AsyncOpenAI(
            api_key=getRagSettings().openai_api_key.get_secret_value(),
        ),
        getRedis(),
        getLogger(),
    )
