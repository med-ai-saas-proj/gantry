from datetime import datetime

from pydantic import BaseModel


class FileUploadResponseDTO(BaseModel):
    """DTO for file upload response."""

    file_id: str


class FileMetadataResponseDTO(BaseModel):
    """DTO for file metadata response."""

    id: str
    filename: str
    content_type: str
    size: int
    storage_path: str
    created_at: datetime
