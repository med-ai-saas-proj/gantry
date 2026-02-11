from datetime import datetime

from pydantic import BaseModel


class FileUploadResponseDTO(BaseModel):
    """DTO for file upload response."""

    file_id: str


class FileMetadataResponseDTO(BaseModel):
    """DTO for file metadata response."""

    id: str
    filename: str
    mime_type: str
    size: int
    storage_path: str
    created_at: datetime


class FilePresignedURLResponseDTO(BaseModel):
    """DTO for file presigned URL response."""

    url: str


class FileMetadataWithPresignedURLResponseDTO(
    FileMetadataResponseDTO, FilePresignedURLResponseDTO
):
    """DTO for file metadata with URL response."""

    pass
