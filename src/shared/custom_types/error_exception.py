from ..settings import getAppSetting
from ..dtos.error_output import ProblemDetails

import traceback
from typing import ClassVar, get_origin


class RecoverableError(Exception):
    status: ClassVar[int] = 500
    title: ClassVar[str]
    code: ClassVar[str]
    detail: ClassVar[str | None] = None
    message: str | None = None
    _stack_frames: list[str] | None
    _from: Exception | None

    def __init__(self, from_exception: Exception | None = None) -> None:
        super().__init__(self.format())
        if getAppSetting().debug:
            self._stack_frames = traceback.format_stack()
        else:
            self._stack_frames = None

        self._from = from_exception

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Iterate over the class annotations (type hints)
        for name, annotation in cls.__annotations__.items():
            # Check if the annotation is strictly a ClassVar
            if get_origin(annotation) is ClassVar:
                # Check if the attribute actually exists in the class
                if not hasattr(cls, name):
                    raise TypeError(
                        f"ClassVar '{name}' was declared but not assigned a value."
                    )

    def format(self) -> ProblemDetails:
        res: ProblemDetails = {"status": self.status, "title": self.title}
        if self.code:
            res.update({"code": self.code})
        if self.detail:
            res.update({"detail": self.detail})
        return res


class UnrecoverableError(Exception):
    detail: ClassVar[str]
    _stack_frames: list[str]
    _from: Exception | None

    def __init__(self, from_exception: Exception | None = None):
        super().__init__()
        self._stack_frames = traceback.format_stack()
        self._from = from_exception

    def format(self) -> ProblemDetails:
        res: ProblemDetails = {"status": 500, "title": "Unrecoverable Error"}
        if self.detail:
            res.update({"detail": self.detail})
        return res


class NotImplementedError(RecoverableError):
    status = 501
    title = "Not Implemented"
    code = "not_implemented"
    detail = "This functionality is not implemented yet."


class NotFoundError(RecoverableError):
    status = 404
    title = "Not Found"
    code = "not_found"
    detail = "The requested resource was not found."


class InvalidEnumValueError(RecoverableError):
    status = 400
    title = "Invalid Enum Value"
    code = "invalid_enum_value"
    detail = "One or more enum values provided are invalid."


class ExternalAPIError(RecoverableError):
    status = 502
    title = "External API Error"
    code = "external_api_error"
    detail = "An error occurred while communicating with an external API."

    def __init__(self, message: str, from_exception: Exception | None = None):
        super().__init__(from_exception)
        self.message = message


class InternalServiceError(UnrecoverableError):
    status = 500
    title = "Internal Service Error"
    code = "internal_service_error"
    detail = "An internal service error occurred. Please contact support."

    def __init__(self, message: str, from_exception: Exception | None = None):
        super().__init__(from_exception)
        self.message = message
