from src.shared.dtos.base import BaseDTO

import uuid
from enum import Enum
from typing import Annotated

from pydantic import Field


class StreamFormat(str, Enum):
    """Stream response format.

    If default, the stream will follow this format.
    A final event will be emit to send the full response,
    the output will be none to save bandwidth. Example:

    - `event: conversation_start`
    - `data: {"conversation_id": "conv_123"}`
    - `event: part_start`
    - `data: thinking`
    - `event: part_delta`
    - `data: {"delta": "Thinking..."}`
    - `event: part_start`
    - `data: output`
    - `event: part_delta`
    - `data: {"delta": "This is"}`
    - `event: part_delta`
    - `data: {"delta": " the result"}`
    - `event: final_result`
    - `event: final_result`
    - `data: {"id": "...", "output": null, "status": "completed", ...}`


    If responses format is ag_ui then the stream will follow
    [AG UI format](https://docs.ag-ui.com/concepts/events)
    """

    default = "default"
    ag_ui = "ag_ui"


class StreamOptions(BaseDTO):
    """Options for streaming responses. Only set this if `stream: true`."""

    response_type: StreamFormat = StreamFormat.default


class GenerationConfig(BaseDTO):
    """Generation config."""

    max_tokens: Annotated[
        int, Field(description="Limit for model output", ge=1)
    ] = 16000


class GenerationInput(BaseDTO):
    """Input for endpoints that use LLM to generate responses."""

    conversation_id: Annotated[
        uuid.UUID | None,
        Field(
            description="The conversation that this response belongs to. "
            "Items from this conversation are prepended to input_items "
            "for this response request. Input items and output items "
            "from this response are automatically added to this "
            "conversation after this response completes."
        ),
    ] = None
    model: Annotated[
        str, Field(description="Model ID used to generate the response.")
    ]
    generation_config: Annotated[
        GenerationConfig, Field(description="Model's generation config")
    ] = GenerationConfig()
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
