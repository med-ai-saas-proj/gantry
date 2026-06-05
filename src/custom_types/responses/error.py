from typing import Any, List, Union
from src.custom_types.common import BaseDict
from src.custom_types.responses import MessagedResponse


class CErrorResponse(MessagedResponse, Exception):
    def __init__(
        self,
        status_code,
        message,
        data: Union[List, BaseDict, Any] = None,
        errors: BaseDict | None = None,
    ):
        super(Exception, self).__init__(message)
        super().__init__(
            status_code=status_code, message=message, data=data, errors=errors
        )
