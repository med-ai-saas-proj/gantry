from src.shared.settings import getAppSetting
from src.shared.custom_types.error_exception import ProblemDetails

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware


__all__ = ["management_app"]

management_app = FastAPI(
    title="Venera API platform",
    openapi_url="/docs/openapi.json",
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

v1_router = APIRouter(
    prefix="/v1", tags=["api", "management", "v1"], include_in_schema=True
)


api_router = APIRouter(
    prefix="/api", tags=["api", "management"], include_in_schema=True
)
api_router.include_router(v1_router)

management_app.include_router(api_router)
