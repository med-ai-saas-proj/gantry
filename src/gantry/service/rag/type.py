from gantry.service.file_storage.types import FileRecord

import enum
import uuid
from typing import Literal, Sequence, TypedDict
from datetime import datetime


class RagQueryRecord(TypedDict):
    file_info: FileRecord | None
    text: str
    embedding: Sequence[float]
    created_at: datetime
    rerank_score: float | None
    bm25_score: float | None
    vector_distance: float | None


class ChunkSplitterType(str, enum.Enum):
    simple = "simple"
    character = "character"
    recursive = "recursive"
    token = "token"
    markdown = "markdown"
    paragraph = "paragraph"
    line = "line"
    spacy = "spacy"


class EmbeddingTask(TypedDict):
    type: Literal["file", "text"]
    task_id: str
    file_id: int | None
    file_uid: uuid.UUID | None
    text: str | list[str] | None
    project_id: int
    project_uuid: uuid.UUID
    chunk_splitter: ChunkSplitterType
    chunk_size: int
    chunk_overlap: int
    status: Literal[
        "pending", "completed", "failed_and_retrying", "failed_and_dropped"
    ]
    failed_reason: str | None
