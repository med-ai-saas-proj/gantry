from .services import FilterQuery, LogFilterKey, KeywordSearchQuery

from typing import Literal
from datetime import datetime

from pydantic import Field, BaseModel


class QueryLogRequest(BaseModel):
    start: datetime = Field(...)
    end: datetime = Field(...)
    limit: int = Field(
        1000, gt=0, le=10000, description="Number of log entries to return"
    )
    direction: Literal["forward", "backward"] = Field(
        "backward", description="Direction to query logs from the start time"
    )
    level: Literal["debug", "info", "warn", "error"] | None
    keyword: list[str | KeywordSearchQuery] | None | str | KeywordSearchQuery
    filters: dict[str | LogFilterKey, str | FilterQuery] | None
    custom_query: str | None = Field(
        default=None,
        description="Custom query string, should be valid Loki Label Filters",
    )
