from .types import MessagePart

from typing import Union, Literal

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Represents a message in a conversation."""

    model_config = {
        "from_attributes": True,
    }

    kind: Union[Literal["response"], Literal["request"]]
    parts: list[MessagePart]

    # metadata fields
    model_name: str | None = None
    timestamp: str | None = None
    run_id: str | None = None
