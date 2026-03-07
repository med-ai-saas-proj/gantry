from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """DTO for file upload response."""

    file_id: str


class FileInfoResponse(BaseModel):
    """DTO for file info response."""

    id: str
    filename: str
    mime_type: str
    size: int
    storage_path: str
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


class UpdateFileMetadataRequest(BaseModel):
    """DTO for updating file metadata."""

    extra_metadata: dict | None