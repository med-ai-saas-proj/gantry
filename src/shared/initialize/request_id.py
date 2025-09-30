import contextvars
from typing import Any


REQUEST_ID_CONTEXTVAR = contextvars.ContextVar[Any](
    "request_id_contextvar", default=None
)
REQUEST_ID_VARS = {}
