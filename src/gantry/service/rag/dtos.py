from gantry.service.file_storage.dtos import FileInfoResponse

from .type import ChunkSplitterType

from uuid import UUID
from typing import Literal, Sequence
from datetime import datetime

from pydantic import Field, BaseModel


class AddRagEmbeddingRequest(BaseModel):
    """DTO for adding an embedding to a RAG bucket."""

    text: str
    lang: str = "simple"
    embedding: Sequence[float]
    file_uid: UUID


class AddRagFileRequest(BaseModel):
    """DTO for adding a file (with embedding) to a RAG bucket."""

    file_uid: UUID
    lang: str = "simple"
    chunk_splitter: ChunkSplitterType = Field(
        default=ChunkSplitterType.recursive
    )
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)


class RagQueryResponse(BaseModel):
    """DTO for RAG query response."""

    file_info: FileInfoResponse
    text: str
    embedding: list[float]
    created_at: datetime


class QueryFilterByFileMetadata(BaseModel):
    """DTO for querying RAG embeddings with file metadata filters."""

    file_metadata_filters: dict[str, str | int | float]


class QueryFilterByFileUid(BaseModel):
    """DTO for querying RAG embeddings with file UID filters."""

    file_uids: Sequence[UUID]


class QueryRagSimilaritySearchRequest(BaseModel):
    """DTO for similarity search within a bucket."""

    embedding: Sequence[float]
    top_k: int = Field(default=5, gt=0, le=100)
    filters: QueryFilterByFileMetadata | QueryFilterByFileUid | None = None


class QueryRagQueryByTextRequest(BaseModel):
    """DTO for querying RAG embeddings by text."""

    query_text: str
    top_k: int = Field(default=5, gt=0, le=100)
    filters: QueryFilterByFileMetadata | QueryFilterByFileUid | None = None

    hybrid_search: bool = Field(
        default=False,
        description="Whether to perform a hybrid search that combines vector similarity and BM25 text search. If true, the service will first use BM25 + semantic search to filter candidates and then rerank them using vector similarity.",
    )
    hybrid_search_bm25_top_k: int = Field(
        default=20,
        gt=0,
        le=1000,
        description="When hybrid_search is true, this parameter controls the number of top candidates to retrieve using BM25 before reranking with vector similarity. A higher value may improve recall but increase latency.",
    )
    hybrid_search_semantic_top_k: int = Field(
        default=100,
        gt=0,
        le=1000,
        description="When hybrid_search is true, this parameter controls the number of top candidates to retrieve using semantic search before reranking with vector similarity. A higher value may improve recall but increase latency.",
    )


class EmbeddingTaskResponse(BaseModel):
    """DTO for RAG embedding task status response."""

    task_id: str
    file_uid: UUID
    project_uuid: UUID
    chunk_splitter: ChunkSplitterType
    chunk_size: int
    chunk_overlap: int
    status: Literal[
        "pending", "completed", "failed_and_retrying", "failed_and_dropped"
    ]
