from .dtos import (
    FileUploadResponseDTO,
    FileMetadataResponseDTO,
    FilePresignedURLResponseDTO,
    FileMetadataWithPresignedURLResponseDTO,
)
from .utils import detect_file_type
from .services import FileStorageService
from .factories import getFileStorageService

import uuid
import mimetypes
from typing import Annotated

from fastapi import Depends, APIRouter, UploadFile, HTTPException
from starlette.responses import RedirectResponse


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

    original_mime_type = file.content_type
    if original_mime_type is None or original_mime_type == "":
        mime_type, ext = detect_file_type(file.file)
    else:
        mime_type = original_mime_type
        ext = mimetypes.guess_extension(mime_type)
        if ext is not None:
            ext = ext.lstrip(".")  # Remove leading dot

    if ext is None and file.filename:
        ext = file.filename.split(".")[-1]  # Fallback to filename extension

    file_id = await file_storage_service.upload_file(
        file.filename or "unknown",
        file.file,
        file.size,
        mime_type,
        ext,
    )
    return FileUploadResponseDTO(
        file_id=str(file_id),
    )


@file_storage_router.get(
    "/{file_id}/download",
    summary="Download a file by file ID.",
    description="Endpoint to download a file by its file ID.",
    responses={
        302: {
            "description": "Redirect to object storage presigned URL for file download.",
            "headers": {
                "Location": {
                    "description": "The URL to redirect to",
                    "schema": {
                        "type": "string",
                        "format": "uri",
                    },
                }
            },
        }
    },
)
async def download_file(
    file_id: uuid.UUID,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Download a file by file ID."""
    presigned_url = (await file_storage_service.get_file_url(file_id)).unwrap()
    return RedirectResponse(url=presigned_url)


@file_storage_router.get(
    "/{file_id}",
    summary="Get file presigned URL and metadata by file ID.",
    description="Endpoint to retrieve file URL and metadata by file ID.",
    response_model=FileMetadataWithPresignedURLResponseDTO,
)
async def get_file_url_and_metadata(
    file_id: uuid.UUID,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Get file URL and metadata by file ID."""
    (
        presigned_url,
        file_metadata,
    ) = (await file_storage_service.get_file_metadata_and_url(file_id)).unwrap()
    return {
        "url": presigned_url,
        "metadata": FileMetadataWithPresignedURLResponseDTO(
            id=str(file_metadata["id"]),
            filename=file_metadata["filename"],
            storage_path=file_metadata["storage_path"],
            mime_type=file_metadata["mime_type"],
            size=file_metadata["size"],
            created_at=file_metadata["created_at"],
            url=presigned_url,
        ),
    }


@file_storage_router.get(
    "/{file_id}/metadata",
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
    file_metadata = (
        await file_storage_service.get_file_metadata(uuid.UUID(file_id))
    ).unwrap()
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
    response_model=FilePresignedURLResponseDTO,
)
async def get_file_presigned_url(
    file_id: uuid.UUID,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Get presigned URL for file download."""
    presigned_url = (await file_storage_service.get_file_url(file_id)).unwrap()
    return FilePresignedURLResponseDTO(
        url=presigned_url,
    )
