from src.service import service_app, service_start_event
from src.management import management_app
from src.shared.utils import request_id_utils
from src.shared.consts import common_const
from src.shared.settings import AppStage, getAppSetting
from src.shared.utils.logger import getLogger
from src.shared.dtos.error_output import (
    ProblemDetails,
)
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

from . import exception_handlers

import time
import uuid
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from pydantic import ValidationError
from opentelemetry import trace
from sqlalchemy.orm import configure_mappers
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.staticfiles import StaticFiles
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)


configure_mappers()

app_settings = getAppSetting()

# 1. Define a Resource (identifies the service)
# This is crucial for your backend to identify which service the data belongs to.
resource = Resource.create(
    {
        "service.name": "main-server",
        "service.version": "0.0.1",
    }
)

# 2. Setup the Tracer Provider
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# 3. Setup the Exporter (OTLP is standard)
# OTLP Exporter sends data to a Collector or compatible backend
otlp_exporter = OTLPSpanExporter(
    # Set your collector/backend URL here (default is usually 'http://localhost:4317')
    endpoint=app_settings.otlp_endpoint,
    insecure=app_settings.stage
    == AppStage.DEV,  # Use for unencrypted local testing
)

# 4. Setup the Span Processor (Batches spans before exporting)
span_processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(span_processor)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = getLogger()
    logger.info("Starting main_app...")
    await service_start_event(logger)
    yield
    logger.info("Shutting down main_app...")

main_app = FastAPI(
    title="Med AI SaaS",
    openapi_url="/docs/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
    responses={
        400: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        500: {"model": ProblemDetails},
    },
)


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

main_app.mount("/", StaticFiles(directory="statics", html=True), name="static")


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
