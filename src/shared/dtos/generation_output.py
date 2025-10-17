from enum import Enum
from typing import Union, Literal, Annotated, TypedDict, NotRequired

from pydantic import Field


class Usage(TypedDict):
    """Number of token used to create this response."""

    input_tokens: Annotated[
        int, Field(description="Number of input token used")
    ]
    output_tokens: Annotated[
        int, Field(description="Number of output token used")
    ]


class Error(TypedDict):
    """Response's error details if it failed, useful for long running task."""

    code: Annotated[str, Field(description="Error code")]
    message: Annotated[str, Field(description="Error message")]
    reason: Annotated[NotRequired[str], Field(description="Reason of error")]


class ResponseStatus(str, Enum):
    """Possible statuses for response.

    - **running**: The response is being process.
    - **error**: The response returned an error.
    - **completd**: The response is completed with no error.
    """

    completed = "completed"
    running = "running"
    error = "error"


class GenerationOutput[T](TypedDict):
    """The root of all LLM related API."""

    id: Annotated[
        str,
        Field(
            description="Output's id, can be used to track long running task"
        ),
    ]
    conversation_id: Annotated[
        str, Field(description="ID of the current conversation")
    ]
    status: Annotated[ResponseStatus, Field(description="Response's status")]
    error: NotRequired[
        Annotated[
            Error,
            Field(
                description=("Error details when the response failed"),
            ),
        ]
    ]
    output: Annotated[
        T,
        Field(description="API's output"),
    ]
    usage: Annotated[
        Usage,
        Field(description="Token usage breakdown for this response"),
    ]
