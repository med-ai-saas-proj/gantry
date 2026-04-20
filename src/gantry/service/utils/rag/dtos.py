from gantry.service.utils.rag.type import ChunkSplitterType
from gantry.service.utils.file_storage.dtos import FileInfoResponse

from uuid import UUID
from typing import Sequence
from datetime import datetime

from pydantic import Field, BaseModel


class AddRagEmbeddingRequest(BaseModel):
    """DTO for adding an embedding to a RAG bucket."""

    text: str
    embedding: Sequence[float]
    file_uid: UUID


class AddRagFileRequest(BaseModel):
    """DTO for adding a file (with embedding) to a RAG bucket."""

    file_uid: UUID
    chunk_splitter: ChunkSplitterType = Field(
        default=ChunkSplitterType.recursive
    )
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)


class RagEmbeddingResponse(BaseModel):
    """DTO for embedding query results."""

    file_info: FileInfoResponse
    text: str
    embedding: list[float]
    created_at: datetime


class QueryRagSimilarRequest(BaseModel):
    """DTO for similarity search within a bucket."""

    embedding: Sequence[float]
    file_ids: Sequence[UUID] | None = None
    top_k: int = Field(default=5, gt=0, le=100)
