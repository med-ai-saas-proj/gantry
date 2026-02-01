from src.service.utils.file_storage.settings import (
    getObjectStorageSettings,
)

from functools import lru_cache

import boto3
from botocore.config import Config


@lru_cache(1)
def getS3Storage():
    """Returns a cached instance of the S3 storage session."""
    object_storage_settings = getObjectStorageSettings()

    return boto3.client(
        "s3",
        region_name=object_storage_settings.s3_region_name,
        aws_access_key_id=object_storage_settings.s3_access_key_id,
        aws_secret_access_key=object_storage_settings.s3_secret_access_key,
        endpoint_url=object_storage_settings.s3_endpoint_url,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # type: ignore
        ),
    )
