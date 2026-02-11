from .dtos import (
    FileUploadResponseDTO,
    FileMetadataResponseDTO,
)
from .types import FileRecord
from .utils import detect_file_type
from .models import FileType
from .services import FileStorageService
from .factories import getFileStorageService

import uuid
import mimetypes
from typing import Annotated

from fastapi import Path, Depends, APIRouter, UploadFile, HTTPException


file_storage_router = APIRouter(prefix="/file-storage", tags=["file-storage"])


@file_storage_router.post(
    "/{file_type}/upload",
    summary="Upload a file to the file storage service.",
    description="Endpoint to upload a file to the file storage service.",
    response_model=FileUploadResponseDTO,
)
async def upload_file(
    file: UploadFile,
    file_type: Annotated[
        FileType, Path(..., description="The type of the file being uploaded.")
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Upload a file to the file storage service."""
    if file.size is None or file.size == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    original_mime_type = file.content_type
    if original_mime_type is None or original_mime_type == "":
        mime_type, ext = detect_file_type(file.file)
    else:
        mime_type = original_mime_type
        ext = mimetypes.guess_extension(mime_type)
        if ext is not None:
            ext = ext.lstrip(".")  # Remove leading dot

    file_id = await file_storage_service.upload_file(
        file.filename or "unknown",
        file.file,
        file.size,
        mime_type,
        ext,
        file_type,
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
    try:
        file_metadata: FileRecord = (
            await file_storage_service.get_file_metadata(uuid.UUID(file_id))
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")
    return FileMetadataResponseDTO(
        id=str(file_metadata["id"]),
        filename=file_metadata["filename"],
        storage_path=file_metadata["storage_path"],
        mime_type=file_metadata["mime_type"],
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
    try:
        presigned_url: str = await file_storage_service.get_file_url(
            uuid.UUID(file_id)
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found.")
    return presigned_url
