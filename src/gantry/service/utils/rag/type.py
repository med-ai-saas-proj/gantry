from gantry.service.utils.file_storage.types import FileRecord

import enum
import uuid
from typing import Literal, Sequence, TypedDict
from datetime import datetime


class RagEmbeddingRecord(TypedDict):
    file_info: FileRecord
    text: str
    embedding: Sequence[float]
    created_at: datetime


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
    task_id: str
    file_id: int
    file_uid: uuid.UUID
    project_id: int
    project_uuid: uuid.UUID
    chunk_splitter: ChunkSplitterType
    chunk_size: int
    chunk_overlap: int
    status: Literal[
        "pending", "completed", "failed_and_retrying", "failed_and_dropped"
    ]
    failed_reason: str | None
