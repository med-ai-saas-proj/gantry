from gantry.service.utils.rag.type import EmbeddingTask
from gantry.management.api_keys.entities import ApiKeyInfo
from gantry.service.utils.file_storage.dtos import FileInfoResponse
from gantry.management.api_keys.dependencies import requiredPermissions

from ..dtos import (
    AddRagFileRequest,
    RagEmbeddingResponse,
    EmbeddingTaskResponse,
    AddRagEmbeddingRequest,
    QueryRagSimilarRequest,
)
from .routers import rag_router
from ..services import RagService
from ..factories import getRagService

import uuid
from typing import Annotated
from collections.abc import Sequence

from fastapi import Body, Depends, Security, APIRouter


rag_service_router = APIRouter(tags=["rag-service"])


@rag_service_router.post(
    "/embeddings",
    summary="Add an embedding row to a RAG bucket.",
    description="Endpoint to add a new embedding row to a RAG bucket.",
    status_code=204,
)
async def add_embedding(
    body: Annotated[AddRagEmbeddingRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.write"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
):
    (
        await rag_service.addEmbedding(
            body.text,
            body.embedding,
            body.file_uid,
            api_key_info["project_id"],
        )
    ).unwrap()


@rag_service_router.get(
    "/files",
    summary="List files in a RAG bucket.",
    description="Endpoint to list distinct file ids stored in a RAG bucket.",
)
async def get_bucket_files(
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.read"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> Sequence[FileInfoResponse]:
    res = await rag_service.getFilesInBucket(api_key_info["project_id"])
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


@rag_service_router.post(
    "/files",
    summary="Add a file to a RAG bucket.",
    description="Endpoint to add a new file to a RAG bucket.",
    status_code=204,
)
async def add_file(
    body: Annotated[AddRagFileRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.write"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> str:
    task_id = (
        await rag_service.addFile(
            body.file_uid,
            api_key_info["project_id"],
            uuid.UUID(api_key_info["project_uuid"]),
            body.chunk_splitter,
            body.chunk_size,
            body.chunk_overlap,
        )
    ).unwrap()
    return task_id


@rag_service_router.get(
    "/files/{task_id}",
    summary="Get RAG file embedding task status.",
    description="Endpoint to get the status of an asynchronous RAG file embedding task.",
)
async def get_task_status(
    task_id: str,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.read"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> EmbeddingTaskResponse:
    """Get the status of an asynchronous RAG embedding task."""
    task_result = (
        await rag_service.getTaskStatus(task_id, api_key_info["project_id"])
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


@rag_service_router.post(
    "/query",
    summary="Query a RAG bucket.",
    description="Endpoint to run a similarity search against a RAG bucket.",
    response_model=list[RagEmbeddingResponse],
)
async def query_bucket(
    body: Annotated[QueryRagSimilarRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.read"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
):
    results = await rag_service.querySimilar(
        api_key_info["project_id"],
        body.embedding,
        body.file_ids,
        body.top_k,
    )
    return [
        RagEmbeddingResponse(
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


rag_router.include_router(rag_service_router, prefix="/service")
