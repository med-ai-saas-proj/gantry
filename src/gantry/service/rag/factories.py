from gantry.db import getRedis, getRedisCacheRepo, getSessionManager
from gantry.service.rag.utils import Reranker
from gantry.shared.logging.logger import getLogger
from gantry.service.file_storage.factories import getFileStorageService
from gantry.management.project.repositories import ProjectRepository
from gantry.service.file_storage.repositories import FileRepository

from .services import RagService
from .settings import getRagSettings

from functools import lru_cache

from openai import AsyncOpenAI


@lru_cache(1)
def getRagService():
    """Returns a cached instance of the RagService."""

    return RagService(
        getSessionManager(),
        ProjectRepository(getRedisCacheRepo()),
        FileRepository(),
        getRagSettings(),
        getFileStorageService(),
        AsyncOpenAI(
            api_key=getRagSettings().embedding_openai_api_key.get_secret_value(),
            base_url=str(getRagSettings().embedding_openai_base_url),
        )
        if getRagSettings().embedding_openai_base_url
        else AsyncOpenAI(
            api_key=getRagSettings().embedding_openai_api_key.get_secret_value(),
        ),
        getRedis(),
        getLogger(),
        Reranker(
            model=getRagSettings().reranker_model,
            api_key=getRagSettings().reranker_api_key.get_secret_value(),
            base_url=str(getRagSettings().reranker_base_url),
        ),
    )
