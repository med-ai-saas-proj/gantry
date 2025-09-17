from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.api.auth import auth_router
from src.api.api_key import api_key_router

# from src.custom_types.responses import C
from .v1 import v1_router
from src.dtos import BaseDTO


class ErrorDetailModel(BaseDTO):
    field: list[str]


class ErrorResponseModel(BaseDTO):
    statusCode: int
    message: str
    error: ErrorDetailModel


api_router = APIRouter(
    prefix="/api",
    default_response_class=JSONResponse,
    responses={
        400: {"model": ErrorResponseModel},
        401: {"model": ErrorResponseModel},
        422: {"model": ErrorResponseModel},
        500: {"model": ErrorResponseModel},
    },
)

api_router.include_router(v1_router)
api_router.include_router(auth_router)
api_router.include_router(api_key_router)
