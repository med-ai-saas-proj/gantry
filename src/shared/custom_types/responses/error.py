from ..base import BaseDict
from ..responses import MessagedResponse

from typing import Any, List, Union


class CErrorResponse(MessagedResponse, Exception):
    def __init__(
        self,
        status_code,
        message,
        data: Union[list, BaseDict, Any] = None,
        errors: BaseDict | None = None,
    ):
        super(Exception, self).__init__(message)
        super().__init__(
            status_code=status_code, message=message, data=data, errors=errors
        )
