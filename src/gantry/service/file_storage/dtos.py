from datetime import datetime

from pydantic import BaseModel, model_validator


class FileUploadResponse(BaseModel):
    """DTO for file upload response."""

    file_id: str


class FileInfoResponse(BaseModel):
    """DTO for file info response."""

    id: str
    filename: str
    mime_type: str
    size: int
    created_at: datetime
    extra_metadata: dict | None


class FilePresignedURLResponse(BaseModel):
    """DTO for file presigned URL response."""

    url: str


class FileInfoWithPresignedURLResponse(
    FileInfoResponse, FilePresignedURLResponse
):
    """DTO for file info with URL response."""

    pass


MAX_METADATA_KEY = 16
MAX_METADATA_KEY_LENGTH = 100
MAX_METADATA_VALUE_LENGTH = 500


class UpdateFileMetadataRequest(BaseModel):
    """DTO for updating file metadata."""

    extra_metadata: dict[str, str | int | float | None] | None

    @model_validator(mode="after")
    def validate_extra_metadata(cls, v):
        if v is not None:
            if len(v) > MAX_METADATA_KEY:
                raise ValueError(
                    f"extra_metadata can have at most {MAX_METADATA_KEY} key-value pairs."
                )
            for key, value in v.items():
                if len(key) > MAX_METADATA_KEY_LENGTH:
                    raise ValueError(
                        f"Metadata keys must be at most {MAX_METADATA_KEY_LENGTH} characters long."
                    )
                if not isinstance(value, (str, int, float, type(None))):
                    raise ValueError(
                        "Metadata values must be of type str, int, float, or None."
                    )
                if (
                    isinstance(value, str)
                    and len(value) > MAX_METADATA_VALUE_LENGTH
                ):
                    raise ValueError(
                        f"Metadata string values must be at most {MAX_METADATA_VALUE_LENGTH} characters long."
                    )
        return v
