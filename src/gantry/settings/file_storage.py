from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings


class ObjectStorageSettings(BaseSettings):
    s3_bucket_name: Annotated[
        str,
        Field(description="S3 bucket name for file storage."),
    ]
    s3_region_name: Annotated[
        str,
        Field(description="AWS region for the S3 bucket."),
    ]
    s3_access_key_id: Annotated[
        str,
        Field(description="AWS access key ID for S3."),
    ]
    s3_secret_access_key: Annotated[
        str,
        Field(description="AWS secret access key for S3."),
    ]
    s3_endpoint_url: Annotated[
        str,
        Field(description="S3-compatible endpoint URL."),
    ]
    s3_presigned_url_expiry_seconds: Annotated[
        int,
        Field(description="Presigned URL expiry time in seconds."),
    ] = 3600
    redis_cache_expiry_seconds: Annotated[
        int,
        Field(
            description="Redis cache expiry for file metadata in seconds.",
        ),
    ] = 3600
