from typing import List

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.responses import JSONResponse
import os

from src.consts.common import MessageConsts
from src.dtos import BaseDTO
from src.routers.chatbot import router as chatbot_router


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

api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])


@api_router.get("/healthcheck", include_in_schema=False)
def healthcheck():
    return JSONResponse(status_code=200, content={"message": MessageConsts.SUCCESS})


@api_router.get("/chatbot.html", include_in_schema=False)
async def serve_chatbot():
    """Serve the chatbot HTML interface"""
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "chatbot.html")

    if os.path.exists(static_path):
        return FileResponse(static_path, media_type="text/html")
    else:
        return JSONResponse(status_code=404, content={"message": "Chatbot interface not found"})
