from gantry.settings import getAppSettings
from gantry.shared.consts.common_const import APP_NAME
from gantry.shared.custom_types.error_exception import ProblemDetails

from .billing import billing_router
from .logging import logging_router
from .project import project_router
from .api_keys import apikey_router
from .organization import org_router

from fastapi import FastAPI, APIRouter
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["management_app"]

app_setting = getAppSettings()


management_app = FastAPI(
    title=APP_NAME,
    openapi_url="/docs/openapi.json" if app_setting.stage == "DEV" else None,
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
    allow_origins=getAppSettings().allowed_origins,
    allow_credentials=True,  # keep only if you really need cookies/auth
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

v1_router = APIRouter(prefix="/v1", tags=["v1"], include_in_schema=True)
v1_router.include_router(apikey_router)
v1_router.include_router(org_router)
v1_router.include_router(billing_router)
v1_router.include_router(project_router)

# api_router = APIRouter(prefix="/api", tags=["api"], include_in_schema=True)
# api_router.include_router(v1_router)

v1_router.include_router(logging_router)

# management_app.include_router(api_router)
management_app.include_router(v1_router)

if app_setting.stage == "DEV":

    @management_app.get("/docs", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=management_app.openapi_url.lstrip("/"),
            title=APP_NAME + " Management API Reference",
        )
