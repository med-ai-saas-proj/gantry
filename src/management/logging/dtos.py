from .services import LogFilterKey, FilterPipeline, SearchPipeline

from typing import Literal, Annotated
from datetime import datetime

from pydantic import Field, BaseModel


class QueryLogRequest(BaseModel):
    start: int | float |  datetime = Field(..., description="int is epoch time in nanoseconds, float is epoch time in seconds")
    end:  int | float | datetime = Field(..., description="int is epoch time in nanoseconds, float is epoch time in seconds")
    limit: int = Field(1000, gt=0, le=10000, description="Number of log entries to return")
    direction: Literal["forward", "backward"] = Field(
        "backward", description="Direction to query logs from the start time"
    )
    level: Literal["debug", "info", "warn", "error"] | None
    search_term: list[str | SearchPipeline] | None | str | SearchPipeline
    filters: dict[str | LogFilterKey, str | FilterPipeline] | None
