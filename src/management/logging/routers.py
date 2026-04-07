from src.settings import getAppSettings
from src.management.auth import UserInfo, getUserInfo

from .dtos import QueryLogRequest
from .factories import getLogQueryService

from typing import Literal, Annotated
from datetime import datetime

from fastapi import Depends, APIRouter
from fastapi.params import Body, Query


logging_router = APIRouter(prefix="/logging", tags=["logging"])


@logging_router.get(
    "/",
    description="Query logs with simple query parameters, suitable for simple queries with only label filters and keyword search. For more complex queries that cannot be easily expressed in query parameters, please use the POST endpoint with a request body.",
)
async def simple_query_log(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    start: Annotated[datetime, Query()],
    end: Annotated[datetime, Query()],
    limit: Annotated[int, Query(le=10000, gt=0)] = 100,
    direction: Annotated[Literal["forward", "backward"], Query()] = "backward",
    level: Annotated[
        Literal["debug", "info", "warn", "error"] | None, Query()
    ] = None,
    keyword: Annotated[str | None, Query()] = None,
    filters: Annotated[
        str | None,
        Query(description="Filters in the format of key:value,key:value"),
    ] = None,
    custom_query: Annotated[
        str | None,
        Query(
            description="Custom query string, should be valid Loki Label Filters",
        ),
    ] = None,
) -> list[dict]:

    app_settings = getAppSettings()
    filters_dict = {}
    for f in filters.split(",") if filters is not None else []:
        key, value = f.split(":")
        filters_dict[key] = value

    log_query_service = getLogQueryService()
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
    app_settings = getAppSettings()

    log_query_service = getLogQueryService()
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
