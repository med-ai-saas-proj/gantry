from .dtos.model import (
    StreamEvent,
    StreamEvent_PartDelta_Output,
    StreamEvent_PartType,
    StreamEvent_FinalResult,
    StreamEventType,
)
from .dtos.generation_output import (
    ResponseStatus,
)

import json
import uuid
from typing import (
    AsyncIterator,
    AsyncGenerator,
    cast,
)

from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.messages import (
    ModelMessage,
    AgentStreamEvent,
)


class StreamHandler:
    """Handles the conversion of agent stream events to SSE streaming and capturing new messages to database after the stream is done."""

    new_messages: list[ModelMessage] | None

    def __init__(
        self,
        conversation_id: int | None,
        conversation_uid: uuid.UUID,
    ):
        self.conversation_id = conversation_id
        self.conversation_uid = conversation_uid
        self.new_messages = None

    async def convertSSEStream[T](
        self,
        agent_stream: AsyncIterator[AgentStreamEvent | AgentRunResultEvent[T]],
    ) -> AsyncGenerator[StreamEvent[T]]:
        yield {
            "event": StreamEventType.conversation_start,
            "data": {
                "conversation_id": str(self.conversation_uid),
            },
        }
        async for event in agent_stream:
            # self.logger.debug("Got new event", new_event=event)
            match event.event_kind:
                case "part_start":
                    part = event.part
                    match part.part_kind:
                        case "text":
                            yield {
                                "event": StreamEventType.part_start,
                                "data": StreamEvent_PartType.output,
                            }
                            if part.has_content():
                                yield {
                                    "event": StreamEventType.part_delta,
                                    "data": {
                                        "type": StreamEvent_PartType.output,
                                        "delta": part.content,
                                    },
                                }
                        case "thinking":
                            yield {
                                "event": StreamEventType.part_start,
                                "data": StreamEvent_PartType.thinking,
                            }
                            if part.has_content():
                                yield {
                                    "event": StreamEventType.part_delta,
                                    "data": {
                                        "type": StreamEvent_PartType.thinking,
                                        "delta": part.content,
                                    },
                                }
                        case "tool-call":
                            yield {
                                "event": StreamEventType.part_start,
                                "data": StreamEvent_PartType.builtin_tool_call,
                            }
                        case "builtin-tool-call":
                            yield {
                                "event": StreamEventType.part_start,
                                "data": StreamEvent_PartType.builtin_tool_call,
                            }
                        case "builtin-tool-return":
                            yield {
                                "event": StreamEventType.part_start,
                                "data": StreamEvent_PartType.builtin_tool_result,
                            }
                        case _:
                            pass
                case "part_delta":
                    mapped_event = StreamEventType.part_delta
                    delta = event.delta
                    match delta.part_delta_kind:
                        case "text":
                            data: StreamEvent_PartDelta_Output = {
                                "type": StreamEvent_PartType.output,
                                "delta": delta.content_delta,
                            }
                            yield {
                                "event": mapped_event,
                                "data": data,
                            }
                        case "thinking":
                            yield {
                                "event": mapped_event,
                                "data": {
                                    "type": StreamEvent_PartType.thinking,
                                    "delta": delta.content_delta,
                                },
                            }
                        case "tool_call":
                            pass
                        case _:
                            pass
                case "function_tool_call":
                    yield {
                        "event": StreamEventType.part_delta,
                        "data": {
                            "type": StreamEvent_PartType.builtin_tool_call,
                            "tool_call_id": event.part.tool_call_id,
                            "hinted_tool_name": event.part.tool_name,
                            "hinted_args": event.part.args_as_json_str(),
                        },
                    }
                case "function_tool_result":
                    # Put part start to signify the end of last part
                    yield {
                        "event": StreamEventType.part_start,
                        "data": StreamEvent_PartType.builtin_tool_result,
                    }
                    yield {
                        "event": StreamEventType.part_delta,
                        "data": {
                            "type": StreamEvent_PartType.builtin_tool_result,
                            "tool_call_id": event.result.tool_call_id,
                            "hinted_result": json.dumps(
                                event.result.content, ensure_ascii=False
                            ),
                        },
                    }
                case "builtin_tool_call":
                    yield {
                        "event": StreamEventType.part_delta,
                        "data": {
                            "type": StreamEvent_PartType.builtin_tool_call,
                            "tool_call_id": event.part.tool_call_id,
                            "hinted_tool_name": event.part.tool_name,
                            "hinted_args": event.part.args_as_json_str(),
                        },
                    }
                case "builtin_tool_result":
                    yield {
                        "event": StreamEventType.part_delta,
                        "data": {
                            "type": StreamEvent_PartType.builtin_tool_result,
                            "tool_call_id": event.result.tool_call_id,
                            "hinted_result": json.dumps(
                                event.result.content, ensure_ascii=False
                            ),
                        },
                    }
                case "final_result":
                    pass
                case "agent_run_result":
                    # self.logger.debug("Got final result")
                    usage = event.result.usage()
                    result: StreamEvent_FinalResult[T] = {
                        "event": StreamEventType.final_result,
                        "data": {
                            "id": cast(str, event.result.run_id),
                            "conversation_id": str(self.conversation_uid),
                            "status": ResponseStatus.completed,
                            "output": event.result.output,
                            "usage": {
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                            },
                        },
                    }
                    yield result
                    self.new_messages = event.result.new_messages()
                case _:
                    pass
