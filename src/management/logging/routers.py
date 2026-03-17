from src.management.auth import UserInfo, getUserInfo
from src.shared.settings import getAppSetting

from .dtos import QueryLogRequest
from .factories import getLogQueryService

import datetime
from typing import Literal, Annotated

from fastapi import Depends, APIRouter
from fastapi.params import Body, Query


logging_router = APIRouter(prefix="/logging")

log_query_service = getLogQueryService()
app_settings = getAppSetting()

@logging_router.get("/")
async def query_log(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    start: int | float | datetime.datetime = Query(..., description="int is epoch time in seconds, float is epoch time in seconds"),
    end: int | float | datetime.datetime = Query(..., description="int is epoch time in seconds, float is epoch time in seconds"),
    limit: int = Query(default=1000, le=10000, gt=0),
    direction: Literal["forward", "backward"] = Query(default="backward"),
    level: Literal["debug", "info", "warn", "error"] | None = Query(default=None),
    search_term: str | None = Query(default=None),
    filters: str | None = Query(default=None, description="Filters in the format of key:value,key:value"),
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
        search_term,
        filters_dict,
    )
    return res.unwrap()

@logging_router.post("/")
async def search_log(
    user_info: Annotated[UserInfo, Depends(getUserInfo)],
    query_request: Annotated[QueryLogRequest, Body()]
) -> list[dict]:
    res = log_query_service.search_logs(
        user_info["org_id"],
        app_settings.app_name,
        query_request.start,
        query_request.end,
        query_request.limit,
        query_request.direction,
        query_request.level,
        query_request.search_term,
        query_request.filters,
    )
    return res.unwrap()
