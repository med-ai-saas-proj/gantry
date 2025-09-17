import json
import time
from typing import Any
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

from src.api import api_router
from src.consts.common import CommonConsts, MessageConsts
from src.consts.env import EnvConsts
from src.custom_types.responses.error import CErrorResponse
from src.dtos.base import PYDANTIC_DISCRIMINATOR_KEY
from src.initialize.request_id import REQUEST_ID_CONTEXTVAR, REQUEST_ID_VARS
from src.utils.logger import LOGGER
from src.utils.request_id import RequestIdUtils


app = FastAPI(
    title="backend",
    description="Welcome to API documentation",
    # root_path="/api/v1",
    docs_url="/docs" if EnvConsts.DEBUG else None,
    # openapi_url="/docs/openapi.json",
    redoc_url="/docs" if EnvConsts.DEBUG else None,
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
        http_code=400,
        status_code=400,
        message=MessageConsts.BAD_REQUEST,
        errors=parsed_errors,
    )
    return JSONResponse(
        status_code=exception_response.http_code,
        content=exception_response.to_dict(),
    )


@app.exception_handler(ValidationError)
async def pydantic_exception_handler(
    request: Request, exception: ValidationError
):
    errors = exception.errors()
    parsed_errors = {}
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
        mssg_list.append(error["msg"])
    exception_response = CErrorResponse(
        http_code=400,
        status_code=400,
        message=MessageConsts.BAD_REQUEST,
        errors=parsed_errors,
    )
    return JSONResponse(
        status_code=exception_response.http_code,
        content=exception_response.to_dict(),
    )


@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exception):
    if isinstance(exception, CErrorResponse):
        error_response = exception.to_dict()
    else:
        errors = None if not EnvConsts.DEBUG else {"key": [str(exception)]}
        exception = CErrorResponse(
            http_code=500,
            status_code=500,
            message=MessageConsts.INTERNAL_SERVER_ERROR,
            errors=errors,
        )
        error_response = exception.to_dict()
    LOGGER.error(json.dumps(error_response))
    return JSONResponse(
        status_code=exception.http_code,
        content=error_response,
    )


@app.middleware("http")
async def global_middleware(request: Request, call_next):
    start_time = time.time_ns() // 1_000_000
    request_id = request.headers.get(CommonConsts.REQUEST_ID_HEADER, None)
    if request_id is None:
        request_id = str(uuid.uuid4())
        new_header = request.headers.mutablecopy()
        new_header[CommonConsts.REQUEST_ID_HEADER] = request_id
        request._headers = new_header
        request.scope["headers"] = new_header.raw
    RequestIdUtils.set(request_id)
    try:
        res: JSONResponse = await call_next(request)
        if res is not None:
            res.headers[CommonConsts.REQUEST_ID_HEADER] = request_id
            process_time = time.time_ns() // 1_000_000 - start_time
            LOGGER.info(
                "Request",
                requestId=request_id,
                latencyMs=process_time,
                method=request.method,
                url=request.url,
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
            url=request.url,
            error=str(e),
        )
        raise
    finally:
        RequestIdUtils.reset()


app.include_router(router=api_router)
