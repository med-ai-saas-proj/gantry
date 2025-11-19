from src.shared.dtos.base import BaseDTO

from .v1 import v1_router

from fastapi import APIRouter
from fastapi.responses import JSONResponse


# class ErrorDetailModel(BaseDTO):
#     field: list[str]


# class ErrorResponseModel(BaseDTO):
#     statusCode: int
#     message: str
#     error: ErrorDetailModel


api_router = APIRouter(
    prefix="/api",
)

api_router.include_router(v1_router)
