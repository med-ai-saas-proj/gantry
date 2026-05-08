from gantry.management.auth.entities import UserInfo, UserInfoWithProjectContext
from gantry.management.project.permissions import ProjectPermission
from gantry.management.project.dependencies import requiredProjectPermission

from ..dtos import (
    RagQueryResponse,
    AddRagFileRequest,
    EmbeddingTaskResponse,
    QueryRagQueryByTextRequest,
)
from .routers import rag_router
from ..services import RagService
from ..factories import getRagService
from ...file_storage.dtos import FileInfoResponse

import uuid
from typing import Sequence, Annotated

from fastapi import Body, Query, Depends, Security, APIRouter


rag_user_router = APIRouter(tags=["rag-user"])


@rag_user_router.get(
    "/files",
    summary="List files in a RAG.",
    description="Endpoint to list distinct file ids stored in a RAG.",
)
async def get_files(
    user_info: Annotated[
        UserInfoWithProjectContext,
        Security(requiredProjectPermission(ProjectPermission.RAG_MANAGE)),
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> Sequence[FileInfoResponse]:
    res = await rag_service.getFilesInRagByProjectUid(user_info["project_uuid"])
    return [
        FileInfoResponse(
            id=str(file_info["uid"]),
            filename=file_info["filename"],
            mime_type=file_info["mime_type"],
            size=file_info["size"],
            created_at=file_info["created_at"],
            extra_metadata=file_info["extra_metadata"],
        )
        for file_info in res
    ]


@rag_user_router.post(
    "/files",
    summary="Add a file to a RAG.",
    description="Endpoint to add a new file to a RAG.",
    status_code=201,
)
async def add_file(
    body: Annotated[AddRagFileRequest, Body()],
    user_info: Annotated[
        UserInfoWithProjectContext,
        Security(requiredProjectPermission(ProjectPermission.RAG_MANAGE)),
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> str:
    task_id = (
        await rag_service.addFileByProjectUid(
            body.file_uid,
            user_info["project_uuid"],
            body.chunk_splitter,
            body.chunk_size,
            body.chunk_overlap,
        )
    ).unwrap()
    return task_id


@rag_user_router.get(
    "/files/{task_id}",
    summary="Get RAG file embedding task status.",
    description="Endpoint to get the status of an asynchronous RAG file embedding task.",
)
async def get_task_status(
    task_id: str,
    user_info: Annotated[
        UserInfoWithProjectContext,
        Security(requiredProjectPermission(ProjectPermission.RAG_MANAGE)),
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> EmbeddingTaskResponse:
    """Get the status of an asynchronous RAG embedding task."""
    task_result = (
        await rag_service.getTaskStatusByProjectUid(
            task_id, user_info["project_uuid"]
        )
    ).unwrap()

    return EmbeddingTaskResponse(
        task_id=task_result["task_id"],
        file_uid=task_result["file_uid"],
        project_uuid=task_result["project_uuid"],
        chunk_splitter=task_result["chunk_splitter"],
        chunk_size=task_result["chunk_size"],
        chunk_overlap=task_result["chunk_overlap"],
        status=task_result["status"],
    )


@rag_user_router.post(
    "/query/text",
    summary="Query a RAG by text.",
    description="Endpoint to run a similarity search against a RAG by text. The service will generate an embedding for the query text and then run the similarity search.",
    response_model=list[RagQueryResponse],
)
async def query_similar_by_text(
    body: Annotated[QueryRagQueryByTextRequest, Body()],
    user_info: Annotated[
        UserInfoWithProjectContext,
        Security(requiredProjectPermission(ProjectPermission.RAG_MANAGE)),
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
    include_embedding: bool = Query(
        default=False,
        description="Whether to include embeddings in the response. Embeddings can be large, so they are excluded by default.",
    ),
):
    results = (
        await rag_service.querySimilarByTextByProjectUid(
            user_info["project_uuid"],
            body.query_text,
            body.filters,
            body.top_k,
            include_embedding,
        )
    ).unwrap()
    return [
        RagQueryResponse(
            file_info=FileInfoResponse(
                id=str(result["file_info"]["uid"]),
                filename=result["file_info"]["filename"],
                mime_type=result["file_info"]["mime_type"],
                size=result["file_info"]["size"],
                created_at=result["file_info"]["created_at"],
                extra_metadata=result["file_info"]["extra_metadata"],
            ),
            text=result["text"],
            embedding=list(result["embedding"]),
            created_at=result["created_at"],
        )
        for result in results
    ]


rag_router.include_router(rag_user_router, prefix="/user")
