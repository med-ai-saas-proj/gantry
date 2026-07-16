from .uuid_utils import uuid7

import contextvars
from typing import Any


REQUEST_ID_CONTEXTVAR = contextvars.ContextVar[str | None](
    "request_id", default=None
)


def get() -> str | None:
    context_id = REQUEST_ID_CONTEXTVAR.get()
    return context_id


def set(request_id: str) -> None:
    REQUEST_ID_CONTEXTVAR.set(request_id)


def reset() -> None:
    REQUEST_ID_CONTEXTVAR.set(None)
