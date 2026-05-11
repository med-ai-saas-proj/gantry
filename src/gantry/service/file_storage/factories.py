from gantry.db.factories import getRedis, getRedisCacheRepo, getSessionManager
from gantry.management.project.repositories import ProjectRepository

from .services import FileStorageService
from .settings import getObjectStorageSettings
from .repositories import FileRepository
from .storage_backend import getS3Storage

from functools import lru_cache


@lru_cache(1)
def getFileStorageService():
    """Returns a cached instance of the FileStorageService."""
    return FileStorageService(
        getS3Storage(),
        getSessionManager(),
        getObjectStorageSettings(),
        FileRepository(),
        getRedis(),
        ProjectRepository(getRedisCacheRepo()),
    )
