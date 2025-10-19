from src.shared.utils import request_id_utils
from src.shared.consts import env_const, common_const, messages_const
from src.shared.dtos.base import PYDANTIC_DISCRIMINATOR_KEY
from src.shared.utils.logger import LOGGER
from src.shared.custom_types.responses.error import CErrorResponse

from .routers import api_router

import json
import time
import uuid
import traceback
from typing import Any

from fastapi import FastAPI, Request
from pydantic import ValidationError
from scalar_fastapi import get_scalar_api_reference
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Venera API",
    description="Welcome to API documentation",
    # root_path="/api/v1",
    docs_url=None,  # "/docs" if env.DEBUG else None,
    openapi_url="/docs/openapi.json",
    redoc_url=None,  # "/docs" if env.DEBUG else None,
)
cors = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def fastapi_exception_handler(
    request: Request, exception: RequestValidationError
):
    errors = exception.errors()
    parsed_errors = {}
    for error in errors:
        locs = error["loc"]
        mssg_list = None
        ref_parsed_errors = parsed_errors
        for loc_i in range(len(locs)):
            loc = locs[loc_i]
            if loc not in ref_parsed_errors:
                ref_parsed_errors[loc] = [] if loc_i == len(locs) - 1 else {}
            if loc_i == len(locs) - 1:
                mssg_list: Any = ref_parsed_errors[loc]
            ref_parsed_errors = ref_parsed_errors[loc]
        mssg_list.append(error["msg"])
    exception_response = CErrorResponse(
        status_code=400,
        message=messages_const.BAD_REQUEST,
        errors=parsed_errors,
    )
    return JSONResponse(
        status_code=exception_response.status_code,
        content=exception_response.to_dict(),
    )


@app.exception_handler(ValidationError)
async def pydantic_exception_handler(
    request: Request, exception: ValidationError
):
    errors = exception.errors()
    parsed_errors = {}
    mssg_list: list[str] | None = None
    for error in errors:
        locs = error["loc"]
        mssg_list = None
        ref_parsed_errors = parsed_errors
        for loc_i in range(len(locs)):
            loc = locs[loc_i]
            if isinstance(loc, str):
                if PYDANTIC_DISCRIMINATOR_KEY in loc:
                    continue
            if loc not in ref_parsed_errors:
                ref_parsed_errors[loc] = [] if loc_i == len(locs) - 1 else {}
            if loc_i == len(locs) - 1:
                mssg_list = ref_parsed_errors[loc]
            ref_parsed_errors = ref_parsed_errors[loc]
        if mssg_list:
            mssg_list.append(error["msg"])
    exception_response = CErrorResponse(
        status_code=400,
        message=messages_const.BAD_REQUEST,
        errors=parsed_errors,
    )
    return JSONResponse(
        status_code=exception_response.status_code,
        content=exception_response.to_dict(),
    )


@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exception):
    if isinstance(exception, CErrorResponse):
        error_response = exception.to_dict()
    else:
        errors = None if not env_const.DEBUG else {"key": str(exception)}
        exception = CErrorResponse(
            status_code=500,
            message=messages_const.INTERNAL_SERVER_ERROR,
            errors=errors,
        )
        error_response = exception.to_dict()
    LOGGER.error(
        json.dumps(error_response),
        traceback=traceback.format_exception(exception),
    )
    return JSONResponse(
        status_code=exception.status_code,
        content=error_response,
    )


@app.middleware("http")
async def global_middleware(request: Request, call_next):
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
            LOGGER.info(
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
        LOGGER.error(
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


app.include_router(router=api_router)


@app.get("/docs", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


app.mount("/", StaticFiles(directory="statics", html=True), name="static")
