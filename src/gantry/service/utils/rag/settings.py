from gantry.service.utils.rag.type import (
    IndexParams,
    RagParameters,
    VectorOpsType,
    VectorIndexType,
)

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class RagSettings(BaseSettings):
    openai_api_key: SecretStr
    embedding_model: str = Field(default="text-embedding-3-small")

    rag_store_parameters: RagParameters = Field(
        default={
            "dimension": 1536,
            "index_params": {
                "index_type": VectorIndexType.hnsw,
                "m": 16,
                "ef_construction": 200,
            },
            "ops_type": VectorOpsType.cosine,
        }
    )


@lru_cache(1)
def getRagSettings() -> RagSettings:
    """Returns a cached instance of RagSettings."""
    return RagSettings()
