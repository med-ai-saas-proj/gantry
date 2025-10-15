"""This file contain definition of chat's data transfer objects."""

from src.shared.dtos.generation_input import GenerationInput
from src.shared.dtos.generation_output import Citation, GenerationOutput

from enum import Enum
from typing import Any, Literal, Sequence, Annotated, TypedDict

from pydantic import Field
from pydantic_ai.messages import ModelMessage


class MultiModalContentType(str, Enum):
    """Content type."""

    image_url = "image_url"
    audio_url = "audio_url"
    video_url = "video_url"
    document_url = "document_url"


class FileURL(TypedDict):
    """Contain file url."""

    url: Annotated[str, Field(description="The file's url, can be base64")]


class ImageURL(FileURL):
    """Image part."""

    type: Literal[MultiModalContentType.image_url]


class AudioURL(FileURL):
    """Audio part."""

    type: Literal[MultiModalContentType.audio_url]


class VideoURL(FileURL):
    """Video part."""

    type: Literal[MultiModalContentType.video_url]


class DocumentURL(FileURL):
    """Document part, can be PDF, text file, word, ..."""

    type: Literal[MultiModalContentType.document_url]
    mime_type: str


MultiModalContent = Annotated[
    ImageURL | AudioURL | VideoURL | DocumentURL,
    Field(discriminator="type", description="Multi modal content type"),
]
ModelInput = str | MultiModalContent
UserInput = str | Sequence[ModelInput]

# class ModelRequestType(str, Enum):
#     user_message = "user_message"
#     tool_result = "tool_result"


# class UserMessage(TypedDict):
#     type: Literal[ModelRequestType.user_message]
#     content: str | Sequence[UserContent]


# class ToolResult(TypedDict):
#     type: Literal[ModelRequestType.tool_result]
#     tool_call_id: str
#     tool_name: str
#     content: Any


class ModelMessageType(str, Enum):
    model_request = "model_request"
    model_response = "model_response"


class ModelRequest(TypedDict):
    """Model request."""

    type: Literal[ModelMessageType.model_request]
    input: UserInput


class ModelResponseContentType(str, Enum):
    text = "text"
    thinking = "thinking"
    # tool_call = "tool_call"


class ModelResponseContentText(TypedDict):
    type: Literal[ModelResponseContentType.text]
    content: str
    citations: list[Citation]


class ModelResponseContentThinking(TypedDict):
    type: Literal[ModelResponseContentType.thinking]
    content: str


# class ModelResponseContentToolCall(TypedDict):
#     type: Literal[ModelResponseContentType.tool_call]
#     tool_call_id: str
#     tool_name: str
#     args: str


ModelResponseContent = Annotated[
    ModelResponseContentText | ModelResponseContentThinking,
    # | ModelResponseContentToolCall,
    Field(discriminator="type", description="Model response content"),
]


class ModelResponse(TypedDict):
    """Model response."""

    type: Literal[ModelMessageType.model_response]
    content: Sequence[ModelResponseContent]


class ChatInput(GenerationInput):
    """Chat input."""

    input: Annotated[UserInput, Field(description="Model's input")]


ChatOutput = Annotated[
    GenerationOutput[Sequence[ModelResponseContent]],
    Field(description="Chat output"),
]
