from gantry.management.auth.roles import ManagementRole
from gantry.management.auth.entities import UserInfo
from gantry.management.auth.dependencies import (
    getUserInfo,
    requireRole,
    check_access_to_project,
)

from ..dtos import (
    FileInfoResponse,
    FileUploadResponse,
    FilePresignedURLResponse,
    UpdateFileMetadataRequest,
    FileInfoWithPresignedURLResponse,
)
from .router import file_storage_router
from ..utils import detect_file_type
from ..services import FileStorageService
from ..factories import getFileStorageService

import uuid
import mimetypes
from typing import Annotated

from fastapi import (
    Body,
    Query,
    Depends,
    Security,
    APIRouter,
    UploadFile,
    HTTPException,
)
from starlette.responses import RedirectResponse


file_storage_user_router = APIRouter(tags=["file-storage-user"])


@file_storage_user_router.post(
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
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_MANAGE))
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to associate the uploaded file with"
    ),
):
    """Upload a file to the file storage service."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

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

    file_id = await file_storage_service.uploadFileByProjectUUID(
        file.filename or "unknown",
        file.file,
        file.size,
        mime_type,
        project_uid,
        ext,
    )
    return FileUploadResponse(
        file_id=str(file_id),
    )


@file_storage_user_router.get(
    "/",
    summary="List files in the file storage service.",
    description="Endpoint to list files in the file storage service.",
    response_model=list[FileInfoResponse],
)
async def list_files(
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_VIEW))
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to list files for"
    ),
):
    """List files in the file storage service."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    files_info = await file_storage_service.listFilesInProjectByUUID(
        project_uid
    )
    return [
        FileInfoResponse(
            id=str(file_info["uid"]),
            filename=file_info["filename"],
            mime_type=file_info["mime_type"],
            size=file_info["size"],
            created_at=file_info["created_at"],
            extra_metadata=file_info["extra_metadata"],
        )
        for file_info in files_info
    ]


@file_storage_user_router.get(
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
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_VIEW))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to download file from"
    ),
):
    """Download a file by file ID."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    presigned_url = (
        await file_storage_service.getFileUrlByProjectUUID(file_id, project_uid)
    ).unwrap()
    return RedirectResponse(url=presigned_url)


@file_storage_user_router.get(
    "/{file_id}",
    summary="Get file info and presigned URL by file ID.",
    description="Endpoint to retrieve file info and a presigned URL for downloading the file by file ID.",
    response_model=FileInfoWithPresignedURLResponse,
)
async def get_file_info_and_presigned_url(
    file_id: uuid.UUID,
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_VIEW))
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to retrieve file from"
    ),
) -> FileInfoWithPresignedURLResponse:
    """Get file URL and info by file ID."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    (
        presigned_url,
        file_info,
    ) = (
        await file_storage_service.getFileInfoAndUrlByProjectUUID(
            file_id, project_uid
        )
    ).unwrap()
    return FileInfoWithPresignedURLResponse(
        id=str(file_info["uid"]),
        filename=file_info["filename"],
        mime_type=file_info["mime_type"],
        size=file_info["size"],
        created_at=file_info["created_at"],
        extra_metadata=file_info["extra_metadata"],
        url=presigned_url,
    )


@file_storage_user_router.get(
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
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_VIEW))
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to retrieve file from"
    ),
):
    """Get file info by file ID."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    file_info = (
        await file_storage_service.getFileInfoByProjectUUID(
            file_id, project_uid
        )
    ).unwrap()
    return FileInfoResponse(
        id=str(file_info["uid"]),
        filename=file_info["filename"],
        mime_type=file_info["mime_type"],
        size=file_info["size"],
        created_at=file_info["created_at"],
        extra_metadata=file_info["extra_metadata"],
    )


@file_storage_user_router.get(
    "/{file_id}/presigned-url",
    summary="Get presigned URL for file download.",
    description="Endpoint to generate a presigned URL for downloading the file.",
    response_model=FilePresignedURLResponse,
)
async def get_file_presigned_url(
    file_id: uuid.UUID,
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_VIEW))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to retrieve file from"
    ),
):
    """Get presigned URL for file download."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    presigned_url = (
        await file_storage_service.getFileUrlByProjectUUID(file_id, project_uid)
    ).unwrap()
    return FilePresignedURLResponse(
        url=presigned_url,
    )


@file_storage_user_router.delete(
    "/{file_id}",
    summary="Delete a file by file ID.",
    description="Endpoint to delete a file from storage by its file ID.",
    status_code=204,
)
async def delete_file(
    file_id: uuid.UUID,
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_MANAGE))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to delete file from"
    ),
):
    """Delete a file by file ID."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    (
        await file_storage_service.deleteFileByProjectUUID(file_id, project_uid)
    ).unwrap()
    return None


@file_storage_user_router.put(
    "/{file_id}/metadata",
    summary="Update file metadata by file ID.",
    description="Endpoint to update file metadata by file ID.",
    status_code=204,
)
async def update_file_metadata(
    file_id: uuid.UUID,
    body: Annotated[UpdateFileMetadataRequest, Body()],
    user_info: Annotated[
        UserInfo, Security(requireRole(ManagementRole.FILE_STORAGE_MANAGE))
    ],
    file_storage_service: Annotated[
        FileStorageService, Depends(getFileStorageService)
    ],
    project_uid: uuid.UUID = Query(
        ..., description="Project UID to update file metadata for"
    ),
):
    """Update file metadata by file ID."""
    check_access_to_project(user_info=user_info, project_uid=project_uid)

    (
        await file_storage_service.updateFileMetadataByProjectUUID(
            file_id, project_uid, body.extra_metadata
        )
    ).unwrap()
    return None


file_storage_router.include_router(file_storage_user_router, prefix="/user")
