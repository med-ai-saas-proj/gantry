from ..custom_types.error_exception import RecoverableError

from typing import TypedDict, NotRequired


class ErrorDetail(TypedDict):
    """An object to provide explicit details on a problem towards an API consumer."""

    detail: str  # max_length 4096
    pointer: NotRequired[str]  # max_length 1024
    parameter: NotRequired[str]  # max_length 1024
    header: NotRequired[str]  # max_length 1024
    code: NotRequired[str]  # max_length 50


class ProblemDetails(TypedDict):
    """Represents the structure for an API Problem Details response."""

    type: NotRequired[str]  # max_length 1024, format 'uri'
    status: int  # minimum 100, maximum 599
    title: str  # max_length 1024
    code: NotRequired[str]  # max_length 50
    detail: NotRequired[str]  # max_length 4096
    errors: NotRequired[list[ErrorDetail]]  # max_items 1000


def problemDetailsFromRecoverableError(
    error: RecoverableError,
) -> ProblemDetails:
    res: ProblemDetails = {"status": error.status, "title": error.title}
    if error.code:
        res.update({"code": error.code})
    if error.detail:
        res.update({"detail": error.detail})
    return res
