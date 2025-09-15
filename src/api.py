from typing import List

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.responses import JSONResponse
import os

from src.consts.common import MessageConsts
from src.dtos import BaseDTO


class ErrorDetailModel(BaseDTO):
    field: List[str]


class ErrorResponseModel(BaseDTO):
    statusCode: int
    message: str
    error: ErrorDetailModel


api_router = APIRouter(
    default_response_class=JSONResponse,
    responses={
        400: {"model": ErrorResponseModel},
        401: {"model": ErrorResponseModel},
        422: {"model": ErrorResponseModel},
        500: {"model": ErrorResponseModel},
    },
)


@api_router.get("/healthcheck", include_in_schema=False)
def healthcheck():
    return JSONResponse(
        status_code=200, content={"message": MessageConsts.SUCCESS}
    )
