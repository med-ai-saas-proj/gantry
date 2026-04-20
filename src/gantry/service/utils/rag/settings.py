from gantry.service.utils.rag.type import (
    IndexParams,
    VectorOpsType,
    VectorIndexType,
    BucketParameters,
)

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class RagSettings(BaseSettings):
    buckets: list[BucketParameters] = Field(
        default=[
            {
                "dimension": 1536,
                "index_params": {
                    "index_type": VectorIndexType.hnsw,
                    "m": 16,
                    "ef_construction": 200,
                },
                "ops_type": VectorOpsType.cosine,
            }
        ],
        min_length=1,
    )


@lru_cache(1)
def getRagSettings() -> RagSettings:
    """Returns a cached instance of RagSettings."""
    return RagSettings()
