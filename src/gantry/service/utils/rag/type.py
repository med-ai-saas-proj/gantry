from gantry.service.utils.file_storage.types import FileRecord

import enum
import uuid
from typing import Literal, Sequence, TypedDict
from datetime import datetime

from alembic.util import status


class RagEmbeddingRecord(TypedDict):
    file_info: FileRecord
    text: str
    embedding: Sequence[float]
    created_at: datetime


class VectorIndexType(str, enum.Enum):
    ivfflat = "ivfflat"
    hnsw = "hnsw"


class VectorOpsType(str, enum.Enum):
    l2 = "vector_l2_ops"  #  <-> (euclidean distance)
    cosine = "vector_cosine_ops"  #  <=> (cosine similarity)
    ip = "vector_ip_ops"  #  <#> (inner product)


class HNSWIndexParams(TypedDict):
    index_type: Literal[VectorIndexType.hnsw]
    m: int
    ef_construction: int


class IVFFlatIndexParams(TypedDict):
    index_type: Literal[VectorIndexType.ivfflat]
    lists: int


type IndexParams = HNSWIndexParams | IVFFlatIndexParams


class RagParameters(TypedDict):
    dimension: int
    index_params: IndexParams
    ops_type: VectorOpsType


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
