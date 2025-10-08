from .base import MessagedResponse
from ..base import BaseDict

from typing import Any, Dict, List, Union


class CPaginationResponse(MessagedResponse):
    def __init__(
        self,
        status_code,
        message,
        data: Union[list, BaseDict, Any],
        page,
        page_size,
        total,
    ):
        super().__init__(status_code=status_code, message=message, data=data)
        self.page = page
        self.page_size = page_size
        self.total = total

    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.page is not None:
            result["page"] = self.page
        if self.page_size is not None:
            result["pageSize"] = self.page_size
        if self.total is not None:
            result["total"] = self.total
        return result
