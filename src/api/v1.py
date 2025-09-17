from typing import List

from fastapi import APIRouter
from starlette.responses import JSONResponse

from src.consts.common import MessageConsts
from src.routers import (
    summary_router,
    api_key_router,
    auth_router,
    rx_advisor_router,
)

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(summary_router)
v1_router.include_router(rx_advisor_router)
v1_router.include_router(api_key_router)
v1_router.include_router(auth_router)


@v1_router.get("/healthcheck")
def healthcheck():
    return JSONResponse(
        status_code=200, content={"message": MessageConsts.SUCCESS}
    )
