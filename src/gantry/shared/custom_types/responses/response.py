from typing import Sequence, TypedDict

from pydantic import BaseModel


class BaseResponse(BaseModel):
    success: bool


class SuccessResponse(BaseResponse):
    success: bool = True


class ErrorResponse(BaseResponse):
    success: bool = False
    error: str


class ObjectResponse[T](SuccessResponse):
    data: T


class ListResponse[T](SuccessResponse):
    data: Sequence[T]


class PaginatedResponse[T](ListResponse[T]):
    total: int
    offset: int
    limit: int
