from enum import Enum
from typing import Annotated, TypedDict, NotRequired, Literal, Union

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


class _ReferenceStartEndIndexMixin(TypedDict):
    start_index: Annotated[
        int,
        Field(
            gt=0,
            description="Index of the first character of the cited reference.",
        ),
    ]
    end_index: Annotated[
        int,
        Field(
            gt=0,
            description="Index of the last character of the cited reference.",
        ),
    ]


class ReferenceType(str, Enum):
    """Types of references that the model makes."""

    document = "document"
    webpage = "webpage"
    inline_text = "inline_text"


class DocumentReference(_ReferenceStartEndIndexMixin):
    """Webpage content that the model is referencing to."""

    type: Literal[ReferenceType.document]
    id: Annotated[
        str,
        Field(description="Id of the referenced document"),
    ]
    title: Annotated[
        str,
        Field(description="Title of the referenced document"),
    ]


class WebpageContent(_ReferenceStartEndIndexMixin):
    """Webpage content (paragraph) that the model is referencing to."""

    id: Annotated[
        str,
        Field(description="Id of the webpage content block"),
    ]
    content: Annotated[
        str,
        Field(
            description=("Text content of the webpage paragraph or block"),
        ),
    ]


class WebpageReference(TypedDict):
    """Webpage that the model is referencing to."""

    type: Literal[ReferenceType.webpage]
    id: Annotated[
        str,
        Field(description="Id of the referenced webpage"),
    ]
    url: Annotated[
        str,
        Field(description="URL of the referenced webpage"),
    ]
    title: Annotated[
        NotRequired[str | None],
        Field(description="Optional title of the webpage"),
    ]
    image_url: Annotated[
        NotRequired[str | None],
        Field(description="Optional image URL representing the webpage"),
    ]
    contents: Annotated[
        list[WebpageContent],
        Field(
            description=(
                "List of content blocks (paragraphs) from the webpage"
            ),
        ),
    ]


class InlineTextReference(_ReferenceStartEndIndexMixin):
    """Previous message that the model is referencing to."""

    type: Literal[ReferenceType.inline_text]
    id: Annotated[
        str,
        Field(
            description=(
                "Id of the inline text (previous message) being referenced"
            ),
        ),
    ]


Reference = Annotated[
    Union[DocumentReference, WebpageReference, InlineTextReference],
    Field(
        discriminator="type",
        description="References used to generate the answer",
    ),
]


class Citation(TypedDict):
    """Citation for the message."""

    start_index: Annotated[
        int,
        Field(
            gt=0,
            description="Index of the first character "
            "in the message that need citing.",
        ),
    ]
    end_index: Annotated[
        int,
        Field(
            gt=0,
            description="Index of the last character "
            "in the message that need citing.",
        ),
    ]
    reference_id: Annotated[
        str,
        Field(
            description="Id of the reference that this citation is"
            " referencing to"
        ),
    ]


class ReferenceCitationMixin(TypedDict):
    """Mixin for references and citations."""

    citation: Annotated[
        list[Citation],
        Field(
            description="Response's citations, model may not cite "
            "all used references"
        ),
    ]
    references: Annotated[
        list[Reference],
        Field(description="References used to generate the response."),
    ]
