from gantry.service.utils.file_storage.types import FileRecord

import enum
from typing import Sequence, TypedDict
from datetime import datetime

from alembic.environment import Literal


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


class BucketParameters(TypedDict):
    dimension: int
    index_params: IndexParams
    ops_type: VectorOpsType
