from typing import Any

import contextvars

CONTEXTVAR = contextvars.ContextVar[Any]("var", default=None)
