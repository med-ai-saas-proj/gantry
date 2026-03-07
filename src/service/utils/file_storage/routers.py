from src.management.api_keys.entities import ApiKeyInfo
from src.management.api_keys.dependencies import requiredPermissions

from .dtos import (
    FileUploadResponse,
    FileInfoResponse,
    FilePresignedURLResponse,
    FileInfoWithPresignedURLResponse,
    UpdateFileMetadataRequest,
)
from .utils import detect_file_type
from .services import FileStorageService
from .factories import getFileStorageService

import uuid
import mimetypes
from typing import Annotated

from fastapi import Body, Depends, Security, APIRouter, UploadFile, HTTPException
from starlette.responses import RedirectResponse


file_storage_router = APIRouter(prefix="/file-storage", tags=["file-storage"])


@file_storage_router.post(
    "/",
    summary="Upload a file to the file storage service.",
    description="Endpoint to upload a file to the file storage service.",
    response_model=FileUploadResponse,
    status_code=201,
)
async def upload_file(
    file: UploadFile,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
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

    file_id = await file_storage_service.uploadFile(
        file.filename or "unknown",
        file.file,
        file.size,
        mime_type,
        api_key_info["project_id"],
        ext,
    )
    return FileUploadResponse(
        file_id=str(file_id),
    )


@file_storage_router.get(
    "/",
    summary="List files in the file storage service.",
    description="Endpoint to list files in the file storage service.",
    response_model=list[FileInfoResponse],
)
async def list_files(
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
):
    """List files in the file storage service."""
    files_info = await file_storage_service.listFilesInProject(
        api_key_info["project_id"]
    )
    return [
        FileInfoResponse(
            id=str(file_info["id"]),
            filename=file_info["filename"],
            storage_path=file_info["storage_path"],
            mime_type=file_info["mime_type"],
            size=file_info["size"],
            created_at=file_info["created_at"],
            extra_metadata=file_info["extra_metadata"],
        )
        for file_info in files_info
    ]


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
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Download a file by file ID."""
    presigned_url = (
        await file_storage_service.getFileUrl(
            file_id, api_key_info["project_id"]
        )
    ).unwrap()
    return RedirectResponse(url=presigned_url)


@file_storage_router.get(
    "/{file_id}",
    summary="Get file presigned URL and info by file ID.",
    description="Endpoint to retrieve file URL and info by file ID.",
    response_model=FileInfoWithPresignedURLResponse,
)
async def get_file_url_and_info(
    file_id: uuid.UUID,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
) -> FileInfoWithPresignedURLResponse:
    """Get file URL and info by file ID."""
    (
        presigned_url,
        file_info,
    ) = (
        await file_storage_service.getFileInfoAndUrl(
            file_id, api_key_info["project_id"]
        )
    ).unwrap()
    return FileInfoWithPresignedURLResponse(
        id=str(file_info["id"]),
        filename=file_info["filename"],
        storage_path=file_info["storage_path"],
        mime_type=file_info["mime_type"],
        size=file_info["size"],
        created_at=file_info["created_at"],
        extra_metadata=file_info["extra_metadata"],
        url=presigned_url,
    )


@file_storage_router.get(
    "/{file_id}/info",
    summary="Get file info by file ID.",
    description="Endpoint to retrieve file info by file ID.",
    response_model=FileInfoResponse,
)
async def get_file_info(
    file_id: uuid.UUID,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
):
    """Get file info by file ID."""
    file_info = (
        await file_storage_service.getFileInfo(
            file_id, api_key_info["project_id"]
        )
    ).unwrap()
    return FileInfoResponse(
        id=str(file_info["id"]),
        filename=file_info["filename"],
        storage_path=file_info["storage_path"],
        mime_type=file_info["mime_type"],
        size=file_info["size"],
        created_at=file_info["created_at"],
        extra_metadata=file_info["extra_metadata"],
    )


@file_storage_router.get(
    "/{file_id}/presigned-url",
    summary="Get presigned URL for file download.",
    description="Endpoint to generate a presigned URL for downloading the file.",
    response_model=FilePresignedURLResponse,
)
async def get_file_presigned_url(
    file_id: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Get presigned URL for file download."""
    presigned_url = (
        await file_storage_service.getFileUrl(
            file_id, api_key_info["project_id"]
        )
    ).unwrap()
    return FilePresignedURLResponse(
        url=presigned_url,
    )


@file_storage_router.delete(
    "/{file_id}",
    summary="Delete a file by file ID.",
    description="Endpoint to delete a file from storage by its file ID.",
    status_code=204,
)
async def delete_file(
    file_id: uuid.UUID,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Delete a file by file ID."""
    (
        await file_storage_service.deleteFile(
            file_id, api_key_info["project_id"]
        )
    ).unwrap()
    return None

@file_storage_router.put(
    "/{file_id}/metadata",
    summary="Update file metadata by file ID.",
    description="Endpoint to update file metadata by file ID.",
    status_code=204,
)
async def update_file_metadata(
    file_id: uuid.UUID,
    body: Annotated[UpdateFileMetadataRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["placeholder"]))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
):
    """Update file metadata by file ID."""
    (
        await file_storage_service.updateFileMetadata(
            file_id, api_key_info["project_id"], body.extra_metadata
        )
    ).unwrap()
    return None