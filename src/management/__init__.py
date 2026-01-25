from src.shared.settings import getAppSetting
from src.shared.custom_types.error_exception import ProblemDetails

from .api_keys import apikey_router
from .api_keys.permission_routes import permission_router

from fastapi import FastAPI, APIRouter
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["management_app"]

management_app = FastAPI(
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

management_app.add_middleware(
    CORSMiddleware,
    allow_origins=getAppSetting().allowed_origins.split(","),
    allow_credentials=True,  # keep only if you really need cookies/auth
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

v1_router = APIRouter(prefix="/v1", tags=["v1"], include_in_schema=True)
v1_router.include_router(apikey_router)
v1_router.include_router(permission_router)


# api_router = APIRouter(prefix="/api", tags=["api"], include_in_schema=True)
# api_router.include_router(v1_router)

# management_app.include_router(api_router)
management_app.include_router(v1_router)


@management_app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=(management_app.openapi_url or "").lstrip("/"),
        title=management_app.title,
    )
