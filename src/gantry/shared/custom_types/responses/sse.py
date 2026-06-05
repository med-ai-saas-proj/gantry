import json
from enum import Enum
from typing import (
    Union,
    TypeVar,
    Iterable,
    TypeAlias,
    TypedDict,
    AsyncIterable,
)

from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask


EventType = TypeVar("EventType", Enum, str, None)
T = TypeVar("T", dict, str, bytes)


class SSEContent[EventType, T](TypedDict):
    event: EventType
    data: T
    # def __init__(self) -> None:
    #     need_prop = ["event", "data"]
    #     for prop in need_prop:
    #         if not hasattr(self, prop):
    #             raise NotImplementedError(
    #                 f"Subclass '{self.__class__.__name__}' must define a '{prop}' attribute."
    #             )

    # def get_event(self) -> EventType:
    #     return self.event

    # def get_data(self) -> T:
    #     return self.data


SSEStream: TypeAlias = Union[AsyncIterable[SSEContent], Iterable[SSEContent]]


class SSEResponse(StreamingResponse):
    def __init__(
        self,
        stream: SSEStream,
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
    async def to_async_iterable(sync_iterable: Iterable[SSEContent]):
        """Converts a synchronous iterable into an asynchronous iterable."""
        for item in sync_iterable:
            # You can add awaitable operations here if needed,
            # for example, to simulate asynchronous work.
            # await asyncio.sleep(0.01)
            yield item

    @staticmethod
    async def stream_format_sse(stream: SSEStream):
        if isinstance(stream, Iterable):
            stream = SSEResponse.to_async_iterable(stream)
        async for content in stream:
            yield SSEResponse.format_sse(content)

    @staticmethod
    def format_sse(content: SSEContent) -> bytes:
        data = content["data"]
        event = content["event"]
        if isinstance(data, bytes):
            result = b"data: " + data + b"\n\n"
        elif isinstance(data, str):
            result = f"data: {data}\n\n".encode()
        else:
            result = (
                f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode()
            )

        if event is not None:
            result = f"event: {event}\n".encode() + result
        return result
