from gantry.service.utils.rag.type import (
    RagParameters,
    VectorOpsType,
    VectorIndexType,
)

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class RagSettings(BaseSettings):
    openai_api_key: SecretStr
    embedding_model: str

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
