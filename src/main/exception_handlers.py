from src.settings import getAppSettings
from src.shared.consts import messages_const
from src.shared.logging.logger import getLogger
from src.shared.dtos.error_output import (
    ProblemDetails,
)
from src.shared.custom_types.error_exception import (
    RecoverableError,
    UnrecoverableError,
)

import traceback

from fastapi import Request
from pydantic import ValidationError
from fastapi.responses import Response, JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError


app_settings = getAppSettings()


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
                "pointer": "/".join(map(str, error["loc"])),
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
