from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class MessagedResponse:
    status_code: int
    message: str
    data: Any = None
    errors: Any = None

    def to_dict(self) -> dict:
        result = {"statusCode": self.status_code, "message": self.message}
        if self.data:
            result["data"] = self.data
        if self.errors:
            result["errors"] = self.errors
        return result
