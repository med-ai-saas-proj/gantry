from .uuid_utils import uuid7
from ..initialize.request_id import (
    REQUEST_ID_VARS,
    REQUEST_ID_CONTEXTVAR,
)


def get() -> str | None:
    context_id = REQUEST_ID_CONTEXTVAR.get()
    if context_id is None:
        return None
    return REQUEST_ID_VARS.get(context_id, None)


def set(request_id: str) -> None:
    context_id = REQUEST_ID_CONTEXTVAR.get()
    if context_id is None:
        context_id = str(uuid7())
    REQUEST_ID_CONTEXTVAR.set(request_id)
    REQUEST_ID_VARS[context_id] = request_id


def reset() -> None:
    context_id = REQUEST_ID_CONTEXTVAR.get()
    if context_id is None:
        return
    REQUEST_ID_VARS.pop(context_id, None)
    REQUEST_ID_CONTEXTVAR.set(None)
