from gantry.service import service_app
from gantry.settings import getAppSettings
from gantry.management import management_app
from gantry.shared.utils import request_id_utils
from gantry.shared.consts import common_const
from gantry.shared.logging.logger import getLogger
from gantry.shared.dtos.error_output import (
    ProblemDetails,
)
from gantry.management.api_keys.permissions import doneRegisterPermission
from gantry.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from . import exception_handlers
from ..otel.setup import setupOtel

import time
import uuid
import traceback

from fastapi import FastAPI, Request, Response
from pydantic import ValidationError
from scalar_fastapi import get_scalar_api_reference
from sqlalchemy.orm import configure_mappers
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


configure_mappers()
doneRegisterPermission()

setupOtel(
    service_name=common_const.APP_NAME,
    service_version=common_const.APP_VERSION,
    logger=getLogger(),
)

main_app = FastAPI(
    title=common_const.APP_NAME,
    openapi_url="/docs/openapi.json"
    if getAppSettings().stage == "DEV"
    else None,
    docs_url=None,
    responses={
        400: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        500: {"model": ProblemDetails},
    },
)

internal_app = FastAPI(
    title=common_const.APP_NAME,
    openapi_url="/docs/internal_openapi.json"
    if getAppSettings().stage == "DEV"
    else None,
    docs_url=None,
)


@main_app.get("/ready")
async def ready():
    return Response(status_code=200)


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


main_app.middleware("http")(global_middleware)
internal_app.middleware("http")(global_middleware)

main_app.mount("/service", service_app, "service")
main_app.mount("/management", management_app, "management")

# main_app.mount("/", StaticFiles(directory="statics", html=True), name="static")


apps = [main_app, service_app, management_app, internal_app]

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


if getAppSettings().stage == "DEV":

    @main_app.get("/docs", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=main_app.openapi_url.lstrip("/"),
            title="Management API Reference",
        )

    @internal_app.get("/internal-docs", include_in_schema=False)
    async def scalar_html2():
        return get_scalar_api_reference(
            openapi_url=internal_app.openapi_url.lstrip("/"),
            title="Management API Reference",
        )
