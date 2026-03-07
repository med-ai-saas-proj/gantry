from src.db.factories import getRedis, getSessionManager
from src.service.utils.file_storage.services import FileStorageService
from src.service.utils.file_storage.settings import getObjectStorageSettings
from src.service.utils.file_storage.repositories import FileRepository
from src.service.utils.file_storage.storage_backend import getS3Storage

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
    )
