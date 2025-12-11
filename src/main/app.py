from src.service import service_app
from src.management import management_app
from src.shared.utils import request_id_utils
from src.shared.consts import common_const, messages_const
from src.shared.settings import AppStage, getAppSetting
from src.shared.utils.logger import getLogger
from src.shared.dtos.error_output import (
    ProblemDetails,
)
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

import time
import uuid
import traceback

from fastapi import FastAPI, Request
from pydantic import ValidationError
from opentelemetry import trace
from scalar_fastapi import get_scalar_api_reference
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)


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

app = FastAPI(
    title="Med AI SaaS",
    responses={
        400: {"model": ProblemDetails},
        401: {"model": ProblemDetails},
        422: {"model": ProblemDetails},
        500: {"model": ProblemDetails},
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.allowed_origins.split(","),
    # allow_credentials=True,               # keep only if you really need cookies/auth
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Api-Key"],
)


@app.exception_handler(RecoverableError)
async def recoverableErrorHandler(
    req: Request, e: RecoverableError
) -> JSONResponse:
    if app_settings.debug:
        assert e._stack_frames is not None
        getLogger().error(
            "Error from",
            exception="".join(traceback.format_exception_only(e)),
            original_exception="".join(
                traceback.format_exception_only(e._from)
            ),
            stack="".join(e._stack_frames),
        )
    return JSONResponse(e.format(), status_code=e.status)


@app.exception_handler(UnrecoverableError)
async def unrecoverableErrorHandler(
    req: Request,
    exception: UnrecoverableError,
):
    logger = getLogger()

    logger.error(
        "Got an unrecoverable error, you should definitely check your code out",
        exception="".join(traceback.format_exception_only(exception)),
        stack="".join(exception._stack_frames),
    )
    if app_settings.debug:
        return Response("".join(exception._stack_frames), status_code=500)
    return Response(messages_const.INTERNAL_SERVER_ERROR, status_code=500)


async def fastapi_exception_handler(
    request: Request,
    exception: RequestValidationError | ResponseValidationError,
):
    errors = exception.errors()
    """
    Error look like this:
    {
        "loc": ["body", "price"],
        "msg": "value is not a valid float",
        "type": "type_error.float"
    }
    """

    exception_response: ProblemDetails = {
        "status": 400,
        "title": messages_const.BAD_REQUEST,
        "errors": [
            {
                "detail": error.get("msg"),
                "header": error.get("type"),
                "pointer": "/".join(error.get("loc", [])),
            }
            for error in errors
        ],
    }
    if app_settings.debug:
        exception_response["type"] = "fast_api_exception_handler"
    return JSONResponse(
        status_code=400,
        content=exception_response,
    )


app.exception_handler(RequestValidationError)(fastapi_exception_handler)
app.exception_handler(ResponseValidationError)(fastapi_exception_handler)


@app.exception_handler(ValidationError)
async def pydantic_exception_handler(
    request: Request, exception: ValidationError
):
    errors = exception.errors()
    exception_response: ProblemDetails = {
        "status": 400,
        "title": messages_const.BAD_REQUEST,
        "errors": [
            {
                "header": error["type"],
                "detail": error["msg"],
                "parameter": ".".join(map(str, error["loc"])),
                "pointer": error.get("url", ""),
            }
            for error in errors
        ],
    }
    if app_settings.debug:
        exception_response["type"] = "pydantic_exception_handler"
        getLogger().error(
            "...", traceback="".join(traceback.format_exception(exception))
        )
    return JSONResponse(
        status_code=400,
        content=exception_response,
    )


@app.exception_handler(Exception)
async def internal_exception_handler(
    request: Request,
    exception: Exception,
):
    logger = getLogger()

    logger.error(
        "Got a weird exception here, you should definitely check your code out!",
        traceback=traceback.format_exception(exception),
    )
    if app_settings.debug:
        return Response(
            status_code=500,
            content="".join(traceback.format_exception(exception)),
        )
    return Response(messages_const.INTERNAL_SERVER_ERROR, status_code=500)


@app.middleware("http")
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


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


app.mount("/service", service_app)
app.mount("/management", management_app)

app.mount("/", StaticFiles(directory="statics", html=True), name="static")
FastAPIInstrumentor.instrument_app(app)
