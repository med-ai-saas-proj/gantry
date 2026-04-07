from src.settings import AppSettings, ModifiedBaseSettings


@AppSettings.register("objectstorage")
class ObjectStorageSettings(ModifiedBaseSettings):
    """Settings for file storage configuration."""

    s3_bucket_name: str
    s3_region_name: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_endpoint_url: str
    s3_presigned_url_expiry_seconds: int = 3600  # in seconds
    redis_cache_expiry_seconds: int = 3600  # in seconds


def getObjectStorageSettings() -> ObjectStorageSettings:
    """Retrieves the file storage settings, cached for performance."""
    return ObjectStorageSettings.get()
