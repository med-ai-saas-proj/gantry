import json
from typing import (
    TypedDict,
    Optional,
    AsyncIterable,
    Iterable,
    Union,
    TypeAlias,
    TypeVar,
)
from enum import Enum
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask


class SSEResponse(StreamingResponse):
    EventType = TypeVar("EventType", Enum, str)
    T = TypeVar("T", dict, str, bytes)

    class Content[EventType, T](TypedDict):
        event: Optional[EventType]
        data: T

    Stream: TypeAlias = Union[AsyncIterable[Content], Iterable[Content]]

    def __init__(
        self,
        stream: Stream,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        media_type: str = "text/event-stream",
        background: BackgroundTask | None = None,
    ):
        super().__init__(
            SSEResponse.stream_format_sse(stream),
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
    async def to_async_iterable(sync_iterable: Iterable[Content]):
        """Converts a synchronous iterable into an asynchronous iterable."""
        for item in sync_iterable:
            # You can add awaitable operations here if needed,
            # for example, to simulate asynchronous work.
            # await asyncio.sleep(0.01)
            yield item

    @staticmethod
    async def stream_format_sse(stream: Stream):
        if isinstance(stream, Iterable):
            stream = SSEResponse.to_async_iterable(stream)
        async for content in stream:
            yield SSEResponse.format_sse(content)

    @staticmethod
    def format_sse(content: Content) -> bytes:
        if isinstance(content["data"], bytes):
            result = b"data: " + content["data"] + b"\n\n"
        elif isinstance(content["data"], str):
            result = f"data: {content['data']}\n\n".encode()
        else:
            result = f"data: {json.dumps(content['data'])}\n\n".encode()

        if content["event"]:
            result = f"event: {content["event"]}\n".encode("utf-8") + result
        return result
