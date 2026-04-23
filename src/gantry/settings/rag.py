import enum
from typing import Literal, TypedDict

from pydantic import SecretStr
from pydantic_settings import BaseSettings


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


class RagSettings(BaseSettings):
    openai_api_key: SecretStr
    openai_base_url: str | None = None
    embedding_model: str

    rag_store_dimension: int = 1536
    rag_store_index_type: VectorIndexType = VectorIndexType.hnsw
    rag_store_index_params_hnsw_m: int = 16
    rag_store_index_params_hnsw_ef_construction: int = 200
    rag_store_index_params_ivfflat_lists: int = 100
    rag_store_ops_type: VectorOpsType = VectorOpsType.cosine

    @property
    def rag_store_parameters(self) -> RagParameters:
        index_params: IndexParams
        if self.rag_store_index_type == VectorIndexType.hnsw:
            index_params = {
                "index_type": VectorIndexType.hnsw,
                "m": self.rag_store_index_params_hnsw_m,
                "ef_construction": self.rag_store_index_params_hnsw_ef_construction,
            }
        elif self.rag_store_index_type == VectorIndexType.ivfflat:
            index_params = {
                "index_type": VectorIndexType.ivfflat,
                "lists": self.rag_store_index_params_ivfflat_lists,
            }
        else:
            raise ValueError(
                f"Unsupported index type: {self.rag_store_index_type}"
            )

        return {
            "dimension": self.rag_store_dimension,
            "index_params": index_params,
            "ops_type": self.rag_store_ops_type,
        }
