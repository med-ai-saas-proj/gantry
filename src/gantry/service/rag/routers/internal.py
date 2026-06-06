from gantry.service.file_storage.dtos import FileInfoResponse

from ..dtos import (
    RagQueryResponse,
    QueryRagQueryByTextRequest,
    QueryRagSimilaritySearchRequest,
)
from ..services import RagService
from ..factories import getRagService

from uuid import UUID
from typing import Annotated
from collections.abc import Sequence

from fastapi import Body, Query, Depends, APIRouter


rag_internal_router = APIRouter(tags=["rag"], prefix="/rag")


@rag_internal_router.get(
    "/files",
    summary="List files in a RAG.",
    description="Endpoint to list distinct file ids stored in a RAG.",
)
async def get_files(
    project_id: Annotated[
        UUID, Query(description="Project ID to which the RAG belongs")
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
) -> Sequence[FileInfoResponse]:
    res = await rag_service.getFilesInRagByProjectUid(project_id)
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


@rag_internal_router.post(
    "/query/text",
    summary="Query a RAG by text.",
    description="Endpoint to run a similarity search against a RAG by text. The service will generate an embedding for the query text and then run the similarity search.",
    response_model=list[RagQueryResponse],
)
async def query_similar_by_text(
    body: Annotated[QueryRagQueryByTextRequest, Body()],
    project_id: Annotated[
        UUID, Query(description="Project ID to which the RAG belongs")
    ],
    rag_service: Annotated[RagService, Depends(getRagService)],
    include_embedding: bool = Query(
        default=False,
        description="Whether to include embeddings in the response. Embeddings can be large, so they are excluded by default.",
    ),
):
    results = (
        await rag_service.querySimilarByTextByProjectUid(
            project_id,
            body.query_text,
            body.filters,
            body.top_k,
            include_embedding,
            body.hybrid_search,
            body.hybrid_search_bm25_top_k,
            body.hybrid_search_semantic_top_k,
            body.hybrid_search_bm25_lang,
        )
    ).unwrap()
    res = []
    for result in results:
        file_info = result.get("file_info")
        res.append(
            RagQueryResponse(
                file_info=FileInfoResponse(
                    id=str(file_info["uid"]),
                    filename=file_info["filename"],
                    mime_type=file_info["mime_type"],
                    size=file_info["size"],
                    created_at=file_info["created_at"],
                    extra_metadata=file_info["extra_metadata"],
                )
                if file_info
                else None,
                text=result["text"],
                embedding=list(result["embedding"]),
                created_at=result["created_at"],
                bm25_score=result.get("bm25_score"),
                rerank_score=result.get("rerank_score"),
                vector_distance=result.get("vector_distance"),
                metadata=result.get("metadata"),
            )
        )
    return res
