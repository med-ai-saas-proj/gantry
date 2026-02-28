"""This file contain definition of chat's data transfer objects."""

from src.shared.custom_types.responses.sse import SSEContent as BaseStreamEvent

from .generation_output import GenerationOutput

import uuid
from enum import Enum
from typing import Literal, NotRequired, Sequence, Annotated, TypedDict

from pydantic import Field, BaseModel, RootModel


class MultiModalContentType(str, Enum):
    """Content type."""

    image = "image"
    audio = "audio"
    video = "video"
    document = "document"


class FileURL(BaseModel):
    """Contain file url."""

    url: Annotated[str, Field(description="The file's url, can be base64")]

class FileId(BaseModel):
    """Contain file id."""
    file_id: Annotated[uuid.UUID, Field(description="The file's id in storage system")]


class ImageBase(BaseModel):
    """Image part."""

    type: Literal[MultiModalContentType.image]


class AudioBase(BaseModel):
    """Audio part."""

    type: Literal[MultiModalContentType.audio]


class VideoBase(BaseModel):
    """Video part."""

    type: Literal[MultiModalContentType.video]


class DocumentBase(BaseModel):
    """Document part, can be PDF, text file, word, ..."""

    type: Literal[MultiModalContentType.document]

class ImageURLInput(ImageBase, FileURL):
    """Image part."""
    pass

class AudioURLInput(AudioBase, FileURL):
    """Audio part."""
    pass

class VideoURLInput(VideoBase, FileURL):
    """Video part."""
    pass

class DocumentURLInput(DocumentBase, FileURL):
    """Document part."""
    mime_type: str | None

class ImageIdInput(ImageBase, FileId):
    """Image part."""
    pass

class AudioIdInput(AudioBase, FileId):
    """Audio part."""
    pass

class VideoIdInput(VideoBase, FileId):
    """Video part."""
    pass

class DocumentIdInput(DocumentBase, FileId):
    """Document part, can be PDF, text file, word, ..."""
    pass

class ImageInput(RootModel):
    root: ImageURLInput | ImageIdInput

class AudioInput(RootModel):
    root: AudioURLInput | AudioIdInput

class VideoInput(RootModel):
    root: VideoURLInput | VideoIdInput

class DocumentInput(RootModel):
    root: DocumentURLInput | DocumentIdInput

type MultiModalContent = Annotated[
    ImageInput | AudioInput | VideoInput | DocumentInput,
    Field(discriminator="type", description="Multi modal content type"),
]
type ModelInputPart = Annotated[str, Field(
    ..., min_length=1
)] | MultiModalContent
type ModelInput = Annotated[str, Field(
    ..., min_length=1
)] | Sequence[ModelInputPart]


class ReferenceType(str, Enum):
    """Types of references that the model makes."""

    document = "document"
    webpage = "webpage"
    inline_text = "inline_text"


class Citation(TypedDict):
    """Citation of the generated messages."""

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
    reference_type: Annotated[
        ReferenceType,
        Field(description="The type of reference this citation uses."),
    ]
    title: Annotated[str, Field(description="Title of the cited reference")]
    src: Annotated[str, Field(description="Source of the cited reference")]
    content: Annotated[str, Field(description="Cited content")]


class ModelMessageType(str, Enum):
    """Types of messages with model."""

    model_request = "model_request"
    model_response = "model_response"


class ModelRequest_ContentType(str, Enum):
    """Model request message type."""

    user_message = "user_message"
    # tool_result = "tool_result"


class ModelRequest_ContentUserMessage(TypedDict):
    """User message model request."""

    type: Literal[ModelRequest_ContentType.user_message]
    content: str | Sequence[ModelInput]


# class ModelRequestContentToolResult(TypedDict):
#     type: Literal[ModelRequestType.tool_result]
#     tool_call_id: str
#     tool_name: str
#     content: Any


type ModelRequest_Content = Annotated[
    ModelRequest_ContentUserMessage,  # | ModelRequestContentToolResult,
    Field(discriminator="type", description="Model Request content"),
]


class ModelRequest(TypedDict):
    """Model request."""

    type: Literal[ModelMessageType.model_request]
    content: ModelRequest_Content


class ModelResponse_ContentType(str, Enum):
    """Model response message type."""

    text = "text"
    thinking = "thinking"
    # tool_call = "tool_call"
    builtin_tool_call = "builtin_tool_call"
    builtin_tool_result = "builtin_tool_result"


class ModelResponse_ContentText(TypedDict):
    """Model response text part."""

    type: Literal[ModelResponse_ContentType.text]
    content: str
    citations: list[Citation]


class ModelResponse_ContentThinking(TypedDict):
    """Model response thinking part."""

    type: Literal[ModelResponse_ContentType.thinking]
    content: str | None


# class ModelResponseContentToolCall(TypedDict):
#     """Model response tool call part."""

#     type: Literal[ModelResponseContentType.tool_call]
#     tool_call_id: str
#     tool_name: str
#     args: str


class ModelResponse_ContentBuiltinToolCall(TypedDict):
    """Model response builting tool call part."""

    type: Literal[ModelResponse_ContentType.builtin_tool_call]
    tool_call_id: str
    hinted_tool_name: str | None
    hinted_args: str | None


class ModelResponse_ContentBuiltinToolResult(TypedDict):
    """Model response builting tool result part."""

    type: Literal[ModelResponse_ContentType.builtin_tool_result]
    tool_call_id: str
    hinted_result: str | None


type ModelResponseContent = Annotated[
    ModelResponse_ContentText
    | ModelResponse_ContentThinking
    | ModelResponse_ContentBuiltinToolCall
    | ModelResponse_ContentBuiltinToolResult,
    # | ModelResponseContentToolCall,
    Field(discriminator="type", description="Model response content"),
]


class ModelResponse(TypedDict):
    """Model response."""

    type: Literal[ModelMessageType.model_response]
    content: Sequence[ModelResponseContent]


class StreamEventType(str, Enum):
    """Stream event type."""

    conversation_start = "conversation_start"
    part_start = "part_start"
    part_delta = "part_delta"
    final_result = "final_result"


class StreamEvent_PartType(str, Enum):
    """Stream part type."""

    output = "output"
    thinking = "thinking"
    builtin_tool_call = "builtin_tool_call"
    builtin_tool_result = "builtin_tool_result"


# class BaseStreamEvent[Event, DataT](TypedDict):
#     """Base Stream event, all stream responses follow this structure."""

#     event: Event
#     data: DataT


class StreamEvent_ConversationStartData(TypedDict):
    """Contain conversation info start."""

    conversation_id: str


type StreamEvent_ConversationStart = BaseStreamEvent[
    Literal[StreamEventType.conversation_start],
    StreamEvent_ConversationStartData,
]

type StreamEvent_PartStart = BaseStreamEvent[
    Literal[StreamEventType.part_start], StreamEvent_PartType
]


class StreamEvent_PartDelta_Output(TypedDict):
    """Contain new output tokens."""

    type: Literal[StreamEvent_PartType.output]
    delta: str | None
    citation: Annotated[
        NotRequired[Citation],
        Field(description="Citation to be added to citation list"),
    ]


class StreamEvent_PartDelta_Thinking(TypedDict):
    """Contain new reasoning output tokens."""

    type: Literal[StreamEvent_PartType.thinking]
    delta: str | None


class StreamEvent_PartDelta_BuiltinToolCall(TypedDict):
    """Contain builtin tool call, we provide hinted name and args for frontend update."""

    type: Literal[StreamEvent_PartType.builtin_tool_call]
    tool_call_id: str
    hinted_tool_name: str | None
    hinted_args: str | None


class StreamEvent_PartDelta_BuiltinToolResult(TypedDict):
    """Signify builtin tool has done execute."""

    type: Literal[StreamEvent_PartType.builtin_tool_result]
    tool_call_id: str
    hinted_result: str | None


type StreamEvent_PartDeltaData = Annotated[
    StreamEvent_PartDelta_Output
    | StreamEvent_PartDelta_Thinking
    | StreamEvent_PartDelta_BuiltinToolCall
    | StreamEvent_PartDelta_BuiltinToolResult,
    Field(discriminator="type"),
]

type StreamEvent_PartDelta = BaseStreamEvent[
    Literal[StreamEventType.part_delta], StreamEvent_PartDeltaData
]

type StreamEvent_FinalResult[T] = BaseStreamEvent[
    Literal[StreamEventType.final_result], GenerationOutput[T]
]

type StreamEvent[T] = Annotated[
    StreamEvent_ConversationStart
    | StreamEvent_PartStart
    | StreamEvent_PartDelta
    | StreamEvent_FinalResult[T],
    Field(discriminator="event", description="Stream events"),
]

type ChatOutput = Annotated[
    GenerationOutput[Sequence[ModelResponseContent]],
    Field(description="Chat output"),
]
