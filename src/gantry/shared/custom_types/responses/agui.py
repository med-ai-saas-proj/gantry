from .sse import SSEStream, SSEContent, SSEResponse

from ag_ui.core import Event
from ag_ui.encoder import EventEncoder
from starlette.background import BackgroundTask


class AGUIResponse(SSEResponse):
    def __init__(
        self,
        stream: SSEStream,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str = "text/event-stream",
        background: BackgroundTask | None = None,
    ):
        super().__init__(
            stream,
            status_code,
            {
                **(headers or {}),
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
            media_type,
            background,
        )

    @staticmethod
    def format_see(content: SSEContent[None, Event]) -> bytes:
        return SSEResponse.format_sse(content)
