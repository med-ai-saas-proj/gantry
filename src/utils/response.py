from typing import Any
import json


class ResponseUtils:
    @staticmethod
    def format_sse(event: str, data: dict[str, Any]):
        return (
            f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        )
