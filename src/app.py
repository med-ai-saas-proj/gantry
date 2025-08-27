import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.responses import JSONResponse

from src.api import api_router
from src.consts.common import MessageConsts
from src.consts.env import EnvConsts
from src.custom_types.responses.error import CErrorResponse
from src.dtos.base import PYDANTIC_DISCRIMINATOR_KEY
from src.utils.logger import LOGGER


app = FastAPI(
    title="backend",
    description="Welcome to API documentation",
    # root_path="/api/v1",
    docs_url="/docs" if EnvConsts.DEBUG else None,
    # openapi_url="/docs/openapi.json",
    redoc_url="/docs" if EnvConsts.DEBUG else None,
)
cors = CORSMiddleware(app, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def fastapi_exception_handler(request: Request, exception: RequestValidationError):
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
        http_code=400, status_code=400, message=MessageConsts.BAD_REQUEST, errors=parsed_errors
    )
    return JSONResponse(
        status_code=exception_response.http_code,
        content=exception_response.to_dict(),
    )


@app.exception_handler(ValidationError)
async def pydantic_exception_handler(request: Request, exception: ValidationError):
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
        http_code=400, status_code=400, message=MessageConsts.BAD_REQUEST, errors=parsed_errors
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


app.include_router(router=api_router)
