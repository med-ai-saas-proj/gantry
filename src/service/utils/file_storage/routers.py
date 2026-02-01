from src.service.utils.file_storage.dtos import (
    FileUploadResponseDTO,
    FileMetadataResponseDTO,
)
from src.service.utils.file_storage.entities import FileRecord
from src.service.utils.file_storage.services import FileStorageService
from src.service.utils.file_storage.factories import getFileStorageService

from typing import Annotated

from fastapi import Depends, APIRouter, UploadFile, HTTPException


file_storage_router = APIRouter(prefix="/file-storage", tags=["file-storage"])


@file_storage_router.post(
    "/upload",
    summary="Upload a file to the file storage service.",
    description="Endpoint to upload a file to the file storage service.",
    response_model=FileUploadResponseDTO,
)
async def upload_file(
    file: UploadFile,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Upload a file to the file storage service."""
    if file.size is None or file.size == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    file_id = await file_storage_service.upload_file(
        file.filename or "unknown", file.file, file.size
    )
    return FileUploadResponseDTO(
        file_id=str(file_id),
    )


@file_storage_router.get(
    "/{file_id}",
    summary="Get file metadata by file ID.",
    description="Endpoint to retrieve file metadata by file ID.",
    response_model=FileMetadataResponseDTO,
)
async def get_file_metadata(
    file_id: str,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Get file metadata by file ID."""
    file_metadata: FileRecord = await file_storage_service.get_file_metadata(
        file_id
    )
    return FileMetadataResponseDTO(
        id=str(file_metadata["id"]),
        filename=file_metadata["filename"],
        storage_path=file_metadata["storage_path"],
        content_type=file_metadata["content_type"],
        size=file_metadata["size"],
        created_at=file_metadata["created_at"],
    )


@file_storage_router.get(
    "/{file_id}/presigned-url",
    summary="Get presigned URL for file download.",
    description="Endpoint to generate a presigned URL for downloading the file.",
    response_model=str,
)
async def get_file_presigned_url(
    file_id: str,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Get presigned URL for file download."""
    presigned_url: str = await file_storage_service.get_file_url(file_id)
    return presigned_url
