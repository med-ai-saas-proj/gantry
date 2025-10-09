from .base import BaseDTO

from enum import Enum
from typing import Annotated

from pydantic import Field


class StreamFormat(str, Enum):
    """Stream response format.

    If default, the stream will follow the format of non stream result,
    no event will be emmitted, only data example:
    - `data: {"summary": "This "}`
    - `data: {"summary": "is "}`
    - `data: {"summary": "a "}`
    - `data: {"summary": "test "}`
    - `data: {"metrics": {"token_used": 33}}`

    If responses format is ag_ui then the stream will follow
    [AG UI format](https://docs.ag-ui.com/concepts/events)
    """

    default = "default"
    ag_ui = "ag_ui"


class StreamOptions(BaseDTO):
    """Options for streaming responses. Only set this if `stream: true`."""

    response_type: StreamFormat = StreamFormat.default


class GenerationInput(BaseDTO):
    """Input for endpoints that use LLM to generate responses."""

    conversation_id: Annotated[
        str | None,
        Field(
            description="The conversation that this response belongs to. "
            "Items from this conversation are prepended to input_items "
            "for this response request. Input items and output items "
            "from this response are automatically added to this "
            "conversation after this response completes."
        ),
    ] = None
    stream: Annotated[
        bool,
        Field(
            description=(
                "If set to true, the model response data will be "
                "streamed to the client as it is generated using "
                "[server-sent events]("
                "https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format)."
            )
        ),
    ] = False
    stream_options: StreamOptions | None = None
