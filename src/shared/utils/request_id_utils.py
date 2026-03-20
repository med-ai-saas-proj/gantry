from .uuid_utils import uuid7

import contextvars
from typing import Any


REQUEST_ID_CONTEXTVAR = contextvars.ContextVar[Any](
    "request_id_contextvar", default=None
)
REQUEST_ID_VARS = {}


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
