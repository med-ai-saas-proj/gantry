from src.shared.custom_types.error_exception import ProblemDetails

from .ocr import ocr_router
from .chat import chat_router
from .ai_search import ai_search_router
from .rx_advisor import rx_advisor_router
from .ehr_summarize import ehr_summarize_router

from fastapi import FastAPI, APIRouter
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["service_app"]

service_app = FastAPI(
    title="Venera API platform",
    openapi_url="/docs/openapi.json",
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
v1_router.include_router(ehr_summarize_router)
v1_router.include_router(rx_advisor_router)
v1_router.include_router(ai_search_router)
v1_router.include_router(ocr_router)
v1_router.include_router(chat_router)

# api_router = APIRouter(prefix="/api", tags=["api"], include_in_schema=True)
# api_router.include_router(v1_router)

# service_app.include_router(api_router)
service_app.include_router(v1_router)


@service_app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=(service_app.openapi_url or "").lstrip("/"),
        title=service_app.title,
    )
