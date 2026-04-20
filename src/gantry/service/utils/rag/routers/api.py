from gantry.management.auth.entities import UserInfo
from gantry.management.api_keys.entities import ApiKeyInfo
from gantry.management.auth.dependencies import getUserInfo
from gantry.service.utils.file_storage.dtos import FileInfoResponse
from gantry.management.api_keys.dependencies import requiredPermissions

from ..dtos import (
    AddRagFileRequest,
    RagEmbeddingResponse,
    AddRagEmbeddingRequest,
    QueryRagSimilarRequest,
    RagBucketConfigResponse,
)
from .routers import rag_router
from ..services import RagService
from ..factories import getRagService

from typing import Annotated
from collections.abc import Sequence

from fastapi import Body, Depends, Security, APIRouter


rag_service_router = APIRouter(tags=["rag-service"])


@rag_service_router.get(
    "/",
    summary="List RAG bucket configurations",
    description="Endpoint to list all RAG bucket configurations.",
    response_model=list[RagBucketConfigResponse],
)
async def get_all_config_api(
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.read"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
):
    buckets = await rag_service.getConfiguredBuckets()
    return [
        RagBucketConfigResponse(
            bucket_idx=i,
            parms=bucket,
        )
        for i, bucket in enumerate(buckets)
    ]


@rag_service_router.post(
    "/{bucket_idx}/embeddings",
    summary="Add an embedding to a RAG bucket.",
    description="Endpoint to add a new embedding row to a RAG bucket.",
    status_code=204,
)
async def add_embedding(
    bucket_idx: int,
    body: Annotated[AddRagEmbeddingRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.write"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
):
    (
        await rag_service.addEmbedding(
            bucket_idx,
            body.text,
            body.embedding,
            body.file_uid,
            api_key_info["project_id"],
        )
    ).unwrap()


@rag_service_router.get(
    "/{bucket_idx}/files",
    summary="List files in a RAG bucket.",
    description="Endpoint to list distinct file ids stored in a RAG bucket.",
)
async def get_bucket_files(
    bucket_idx: int,
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.read"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> Sequence[FileInfoResponse]:
    res = await rag_service.getFilesInBucket(
        bucket_idx, api_key_info["project_id"]
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
        for file_info in res
    ]


@rag_service_router.post(
    "/{bucket_idx}/embeddings",
    summary="Add an embedding to a RAG bucket.",
    description="Endpoint to add a new embedding row to a RAG bucket.",
    status_code=204,
)
async def add_file(
    bucket_idx: int,
    body: Annotated[AddRagFileRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.write"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
):
    (
        await rag_service.addFile(
            bucket_idx,
            body.file_uid,
            api_key_info["project_id"],
        )
    ).unwrap()


@rag_service_router.post(
    "/{bucket_idx}/query",
    summary="Query a RAG bucket.",
    description="Endpoint to run a similarity search against a RAG bucket.",
    response_model=list[RagEmbeddingResponse],
)
async def query_bucket(
    bucket_idx: int,
    body: Annotated[QueryRagSimilarRequest, Body()],
    api_key_info: Annotated[
        ApiKeyInfo, Security(requiredPermissions(["rag.read"]))
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
):
    results = await rag_service.querySimilar(
        bucket_idx,
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
