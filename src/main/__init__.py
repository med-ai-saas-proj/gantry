from src.service import service_app
from src.settings import getAppSettings
from src.management import management_app
from src.logging.otel import setupOtel
from src.shared.utils import request_id_utils
from src.shared.consts import common_const
from src.shared.logging.logger import getLogger
from src.shared.dtos.error_output import (
    ProblemDetails,
)
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from . import exception_handlers
from ..service.lifespan import (
    startup as service_startup,
    shutdown as service_shutdown,
)

import time
import uuid
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def mainMainMain():
    configure_mappers()

    app_settings = getAppSettings()

    setupOtel(
        service_name=app_settings.app_name,
        service_version=app_settings.app_version,
        logger=getLogger(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code here
    await service_startup(app)
    yield

    # Shutdown code here
    await service_shutdown(app)


main_app = FastAPI(
    title="Med AI SaaS",
    openapi_url="/docs/openapi.json",
    docs_url="/docs",
    responses={
        400: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        500: {"model": ProblemDetails},
    },
    lifespan=lifespan,
)


@main_app.get("/ready")
async def ready():
    return Response(status_code=200)


@main_app.middleware("http")
async def global_middleware(
    request: Request,
    call_next,
):
    logger = getLogger()

    start_time = time.time_ns() // 1_000_000
    request_id = request.headers.get(common_const.REQUEST_ID_HEADER, None)
    if request_id is None:
        request_id = str(uuid.uuid4())
        new_header = request.headers.mutablecopy()
        new_header[common_const.REQUEST_ID_HEADER] = request_id
        request._headers = new_header
        request.scope["headers"] = new_header.raw
    request_id_utils.set(request_id)
    try:
        res: Response = await call_next(request)
        if res is not None:
            res.headers[common_const.REQUEST_ID_HEADER] = request_id
            process_time = time.time_ns() // 1_000_000 - start_time
            logger.info(
                "Request",
                requestId=request_id,
                latencyMs=process_time,
                method=request.method,
                url=str(request.url),
                status=res.status_code,
            )
        return res
    except Exception as e:
        process_time = time.time_ns() // 1_000_000 - start_time
        logger.error(
            "Request failed",
            requestId=request_id,
            latencyMs=process_time,
            method=request.method,
            url=str(request.url),
            error=str(e),
            traceback=traceback.format_exception(e),
        )
        raise
    finally:
        request_id_utils.reset()


main_app.mount("/service", service_app, "service")
main_app.mount("/management", management_app, "management")

# main_app.mount("/", StaticFiles(directory="statics", html=True), name="static")


apps = [main_app, service_app, management_app]

handler_map = {
    RecoverableError: exception_handlers.recoverableErrorHandler,
    UnrecoverableError: exception_handlers.recoverableErrorHandler,
    RequestValidationError: exception_handlers.fastapi_exception_handler,
    ResponseValidationError: exception_handlers.fastapi_exception_handler,
    ValidationError: exception_handlers.pydantic_exception_handler,
    Exception: exception_handlers.internal_exception_handler,
}

for app in apps:
    for exc, handler in handler_map.items():
        app.exception_handler(exc)(handler)
    FastAPIInstrumentor.instrument_app(app)
