from src.shared.custom_types.error_exception import ProblemDetails

# from .chat import chat_router
# from .ai_search import ai_search_router
from .utils.conversation import conversation_router
from .utils.file_storage import file_storage_router

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["service_app"]


service_app = FastAPI(
    title="Venera API platform",
    openapi_url="/docs/openapi.json",
    docs_url="/docs",
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
