from src.settings import AppSettings, ObjectStorageSettings


def getObjectStorageSettings() -> ObjectStorageSettings:
    """Retrieves the file storage settings, cached for performance."""
    return AppSettings.get().file_storage
