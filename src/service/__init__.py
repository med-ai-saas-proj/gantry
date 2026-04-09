from src.settings import AppSettings
from src.shared.custom_types.error_exception import ProblemDetails

from .utils.conversation import conversation_router
from .utils.file_storage import file_storage_router

from fastapi import FastAPI, APIRouter
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["service_app"]

app_setting = AppSettings.get()

service_app = FastAPI(
    title=app_setting.app_name,
    openapi_url=app_setting.openapi_json_path
    if app_setting.stage == "DEV"
    else None,
    docs_url=None,
    responses={
        400: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        500: {"model": ProblemDetails},
    },
)

service_app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,  # keep only if you really need cookies/auth
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # allow_headers=["Content-Type", "X-Api-Key"],
    allow_headers=["*"],
)

v1_router = APIRouter(prefix="/v1", tags=["service"], include_in_schema=True)
# v1_router.include_router(ai_search_router)
# v1_router.include_router(chat_router)
v1_router.include_router(file_storage_router)
v1_router.include_router(conversation_router)

# api_router = APIRouter(prefix="/api", tags=["api"], include_in_schema=True)
# api_router.include_router(v1_router)

# service_app.include_router(api_router)
service_app.include_router(v1_router)

if app_setting.stage == "DEV":

    @service_app.get(app_setting.docs_url, include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app_setting.openapi_json_path.lstrip("/"),
            title=app_setting.app_name + " API Reference",
        )
