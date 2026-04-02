from src.management.auth import UserInfo, getUserInfo
from src.shared.settings import getAppSetting

from .dtos import QueryLogRequest
from .factories import getLogQueryService

from typing import Literal, Annotated
from datetime import datetime

from fastapi import Depends, APIRouter
from fastapi.params import Body, Query


logging_router = APIRouter(prefix="/logging", tags=["logging"])

log_query_service = getLogQueryService()
app_settings = getAppSetting()


@logging_router.get(
    "/",
    description="Query logs with simple query parameters, suitable for simple queries with only label filters and keyword search. For more complex queries that cannot be easily expressed in query parameters, please use the POST endpoint with a request body.",
)
async def simple_query_log(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(default=1000, le=10000, gt=0),
    direction: Literal["forward", "backward"] = Query(default="backward"),
    level: Literal["debug", "info", "warn", "error"] | None = Query(
        default=None
    ),
    keyword: str | None = Query(default=None),
    filters: str | None = Query(
        default=None, description="Filters in the format of key:value,key:value"
    ),
    custom_query: str | None = Query(
        default=None,
        description="Custom query string, should be valid Loki Label Filters",
    ),
) -> list[dict]:
    filters_dict = {}
    for f in filters.split(",") if filters is not None else []:
        key, value = f.split(":")
        filters_dict[key] = value

    res = log_query_service.search_logs(
        user_info["org_id"],
        app_settings.app_name,
        start,
        end,
        limit,
        direction,
        level,
        keyword,
        filters_dict,
        custom_query,
    )
    return res.unwrap()


@logging_router.post(
    "/",
    description="Query logs with more complex request body, supports keyword search and filters with operators (e.g. >, <, =) and custom Loki Label Filters through custom_query field. The GET endpoint is more suitable for simple queries with only label filters and no keyword search, while this POST endpoint can handle more complex queries that cannot be easily expressed in query parameters.",
)
async def query_log(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    query_request: Annotated[QueryLogRequest, Body()],
) -> list[dict]:
    res = log_query_service.search_logs(
        user_info["org_id"],
        app_settings.app_name,
        query_request.start,
        query_request.end,
        query_request.limit,
        query_request.direction,
        query_request.level,
        query_request.keyword,
        query_request.filters,
    )
    return res.unwrap()
