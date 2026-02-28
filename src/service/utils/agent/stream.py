import asyncio

from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.file_storage.utils import (
    detect_file_type,
)
from src.service.utils.conversation.services import ConversationService

from .dtos.model import (
    ChatOutput,
    ModelInput,
    StreamEvent,
    StreamEvent_PartDelta,
    StreamEvent_PartStart,
    StreamEventType,
    ModelResponseContent,
    StreamEvent_PartType,
    StreamEvent_FinalResult,
    ModelResponse_ContentType,
)
from .dtos.generation_output import (
    ResponseStatus,
    GenerationOutput,
)
from ..file_storage.factories import getFileStorageService

import json
import uuid
import base64
from typing import (
    Sequence,
    AsyncIterator,
    AsyncGenerator,
    cast,
)

from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.messages import (
    AudioUrl,
    ImageUrl,
    VideoUrl,
    DocumentUrl,
    UserContent,
    ModelRequest,
    ModelResponse,
    AgentStreamEvent,
)


def _create_new_part(event: StreamEvent) -> ModelResponseContent:
    match event["data"]:
        case StreamEvent_PartType.output:
            return {
                "type": ModelResponse_ContentType.text,
                "content": "",
                "citations": [],
            }
        case StreamEvent_PartType.thinking:
            return {
                "type": ModelResponse_ContentType.thinking,
                "content": None,
            }
        case StreamEvent_PartType.builtin_tool_call:
            return {
                "type": ModelResponse_ContentType.builtin_tool_call,
                "tool_call_id": "",
                "hinted_tool_name": None,
                "hinted_args": None,
            }
        case StreamEvent_PartType.builtin_tool_result:
            return {
                "type": ModelResponse_ContentType.builtin_tool_result,
                "tool_call_id": "",
                "hinted_result": None,
            }
        case _:
            raise RuntimeError(
                "New type, check out create new part", __file__, event
            )


async def aggregateStream[T](
    stream: AsyncGenerator[StreamEvent[T]],
) -> ChatOutput:
    # Why does this instead of run_sync?
    # Anthropic said: non-streaming Messages API requests are not expected
    # to exceed a 10 minute timeout
    # https://docs.anthropic.com/en/api/errors#long-requests

    event_part_map: dict[StreamEvent_PartType, ModelResponse_ContentType] = {
        StreamEvent_PartType.output: ModelResponse_ContentType.text,
        StreamEvent_PartType.thinking: ModelResponse_ContentType.thinking,
        StreamEvent_PartType.builtin_tool_call: ModelResponse_ContentType.builtin_tool_call,
        StreamEvent_PartType.builtin_tool_result: ModelResponse_ContentType.builtin_tool_result,
    }

    final_output: GenerationOutput[T] | None = None
    model_response: list[ModelResponseContent] = []
    last_part: ModelResponseContent | None = None

    async for output in stream:
        match output["event"]:
            case StreamEventType.conversation_start:
                pass
            case StreamEventType.part_start:
                if (
                    last_part
                    and last_part["type"] != event_part_map[output["data"]]
                ):
                    model_response.append(last_part)
                    last_part = _create_new_part(output)
                if last_part is None:
                    last_part = _create_new_part(output)
            case StreamEventType.part_delta:
                part_delta_data = output["data"]
                if (
                    last_part
                    and last_part["type"]
                    != event_part_map[part_delta_data["type"]]
                ):
                    model_response.append(last_part)
                    last_part = _create_new_part(output)
                assert last_part is not None, (
                    "Check ai search stream aggregation"
                )
                match part_delta_data["type"]:
                    case StreamEvent_PartType.output:
                        assert (
                            last_part["type"] == ModelResponse_ContentType.text
                        ), last_part["type"]
                        last_part["content"] += part_delta_data["delta"] or ""
                        citation = part_delta_data.get("citation")
                        if citation is not None:
                            last_part["citations"].append(citation)
                    case StreamEvent_PartType.thinking:
                        assert (
                            last_part["type"]
                            == ModelResponse_ContentType.thinking
                        ), last_part["type"]
                        if part_delta_data["delta"]:
                            if last_part["content"] is None:
                                last_part["content"] = ""
                            last_part["content"] += part_delta_data["delta"]
                    case StreamEvent_PartType.builtin_tool_call:
                        assert (
                            last_part["type"]
                            == ModelResponse_ContentType.builtin_tool_call
                        ), last_part["type"]
                        last_part["tool_call_id"] = part_delta_data["tool_call_id"]
                        last_part["hinted_tool_name"] = part_delta_data["hinted_tool_name"]
                        last_part["hinted_args"] = part_delta_data["hinted_args"]
                    case StreamEvent_PartType.builtin_tool_result:
                        assert (
                            last_part["type"]
                            == ModelResponse_ContentType.builtin_tool_result
                        ), last_part["type"]
                        last_part["tool_call_id"] = part_delta_data["tool_call_id"]
                        last_part["hinted_result"] = part_delta_data["hinted_result"]
                    case _:
                        pass
            case StreamEventType.final_result:
                if last_part is not None:
                    model_response.append(last_part)
                final_output = output["data"]

    assert final_output is not None, "Check ai search stream aggregation"
    final_output_ = cast(ChatOutput, final_output)
    final_output_["output"] = model_response
    return final_output_

