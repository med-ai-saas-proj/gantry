from fastapi import APIRouter

from src.auth_v2.routes import api_keys, auth, test
from src.shared.consts import messages_const
from src.shared.custom_types.responses import MessagedResponse

v2_router = APIRouter(prefix="/v2")

v2_router.include_router(api_keys.router)
v2_router.include_router(auth.router)

v2_router.include_router(test.router)

@v2_router.get("/healthcheck", response_model=MessagedResponse)
def healthcheck():
    return MessagedResponse(status_code=200, message=messages_const.SUCCESS)
