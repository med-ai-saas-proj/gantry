import enum
from re import S
from typing import Literal, Annotated, TypedDict

from pydantic import Field, HttpUrl, SecretStr
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
    half_precision: bool
    dimension: int
    index_params: IndexParams
    ops_type: VectorOpsType


class RagSettings(BaseSettings):
    embedding_model: Annotated[
        str,
        Field(description="Model to use for generating embeddings."),
    ]
    embedding_openai_api_key: Annotated[
        SecretStr,
        Field(description="OpenAI API key for RAG functionality."),
    ]
    embedding_openai_base_url: Annotated[
        HttpUrl,
        Field(description="Base URL for the OpenAI API."),
    ]
    reranker_model: Annotated[
        str,
        Field(
            description="Model to use for re-ranking RAG results. This can be the same as the embedding model or a different one optimized for ranking."
        ),
    ]
    reranker_api_key: Annotated[
        SecretStr,
        Field(description="OpenAI API key for the re-ranker model."),
    ]
    reranker_base_url: Annotated[
        HttpUrl,
        Field(
            description="Base URL for the OpenAI API for the re-ranker model."
        ),
    ]
    supported_langs: Annotated[
        str,
        Field(
            description="List of supported languages for bm25 separated by commas. For example: 'simple,english,french'.  The 'lang' field in RagData can only take values from this list."
        ),
    ] = "simple"  # default to 'simple' which can be used for language

    rag_store_half_precision: Annotated[
        bool,
        Field(
            description="Whether to use half-precision (float16) for storing embeddings in the RAG store. This can reduce memory usage and improve performance on compatible hardware, but may lead to slightly lower accuracy."
        ),
    ] = True
    rag_store_dimension: Annotated[
        int,
        Field(
            description="Dimensionality of the vector embeddings stored in the RAG store."
        ),
    ] = 1536
    rag_store_index_type: Annotated[
        VectorIndexType,
        Field(description="Type of vector index to use for the RAG store."),
    ] = VectorIndexType.hnsw
    rag_store_index_params_hnsw_m: Annotated[
        int,
        Field(
            description="HNSW index parameter 'm', which controls the number of bi-directional links created for each new element during index construction."
        ),
    ] = 16
    rag_store_index_params_hnsw_ef_construction: Annotated[
        int,
        Field(
            description="HNSW index parameter 'ef_construction', which controls the accuracy/speed trade-off during index construction. Higher values lead to better recall but slower indexing."
        ),
    ] = 200
    rag_store_index_params_ivfflat_lists: Annotated[
        int,
        Field(
            description="IVFFlat index parameter 'lists', which determines the number of Voronoi cells (or clusters) used in the index. More lists can improve recall but may increase search time."
        ),
    ] = 100
    rag_store_ops_type: Annotated[
        VectorOpsType,
        Field(
            description="Type of vector operations to use for similarity search in the RAG store."
        ),
    ] = VectorOpsType.cosine

    @property
    def supported_langs_list(self) -> list[str]:
        return [
            lang.strip()
            for lang in self.supported_langs.split(",")
            if lang.strip()
        ]

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
            "half_precision": self.rag_store_half_precision,
        }
