from src.main import app
from src.shared.settings import getAppSetting
from src.shared.custom_types.error_exception import ProblemDetails

from .billing import billing_router
from .logging import logging_router
from .project import project_router
from .api_keys import apikey_router
from .organization import org_router
from .organization.settings import getOrgSettings
from .organization.factories import getOrgService

import asyncio
import contextlib

from fastapi import FastAPI, APIRouter
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["management_app"]

app_setting = getAppSetting()


async def _org_delete_worker_loop():
    service = getOrgService()
    while True:
        try:  # noqa: SIM105
            await service.processDueDeletions()
        except Exception:
            # Keep loop alive; failures are logged in service/global handlers.
            pass
        await asyncio.sleep(getOrgSettings().deletion_worker_interval_seconds)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    org_deletion_task = asyncio.create_task(_org_delete_worker_loop())
    yield
    org_deletion_task.cancel()
    try:
        await org_deletion_task
    except Exception:
        pass


management_app = FastAPI(
    title=app_setting.app_name,
    openapi_url=app_setting.openapi_json_path
    if app_setting.stage == "DEV"
    else None,
    docs_url=None,
    lifespan=lifespan,
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
v1_router.include_router(org_router)
v1_router.include_router(billing_router)
v1_router.include_router(project_router)

# api_router = APIRouter(prefix="/api", tags=["api"], include_in_schema=True)
# api_router.include_router(v1_router)

v1_router.include_router(logging_router)

# management_app.include_router(api_router)
management_app.include_router(v1_router)

if app_setting.stage == "DEV":

    @management_app.get(app_setting.docs_url, include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app_setting.openapi_json_path.lstrip("/"),
            title=app_setting.app_name + " Management API Reference",
        )
