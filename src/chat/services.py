from src.chat.dtos import (
    ChatOutput,
    StreamEvent,
    ReferenceType,
    StreamEventType,
    ModelResponseContent,
    StreamEvent_PartType,
    StreamEvent_FinalResult,
    ModelResponse_ContentType,
    StreamEvent_PartDelta_Output,
)
from src.db.postgres.service import PostgresService
from src.shared.dtos.generation_output import (
    ResponseStatus,
    GenerationOutput,
)

import json
from typing import (
    Callable,
    Sequence,
    AsyncGenerator,
    cast,
)
from contextlib import _GeneratorContextManager

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger
from pydantic_ai.messages import ModelRequest, ModelResponse


def _create_new_part(event: StreamEvent) -> ModelResponseContent:
    match event:
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
            raise RuntimeError("New type, check out create new part", __file__)


async def aggregate_stream(
    stream: AsyncGenerator[StreamEvent],
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

    final_output: GenerationOutput[None] | None = None
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
                        if "citation" in part_delta_data:
                            last_part["citations"].append(
                                part_delta_data["citation"]
                            )
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
                        last_part["tool_call_id"] = part_delta_data[
                            "tool_call_id"
                        ]
                        last_part["hinted_tool_name"] = part_delta_data[
                            "hinted_tool_name"
                        ]
                        last_part["hinted_args"] = part_delta_data[
                            "hinted_args"
                        ]
                    case StreamEvent_PartType.builtin_tool_result:
                        assert (
                            last_part["type"]
                            == ModelResponse_ContentType.builtin_tool_result
                        ), last_part["type"]
                        last_part["tool_call_id"] = part_delta_data[
                            "tool_call_id"
                        ]
                        last_part["hinted_result"] = part_delta_data[
                            "hinted_result"
                        ]
                    case _:
                        pass
            case StreamEventType.final_result:
                final_output = output["data"]

    assert final_output is not None, "Check ai search stream aggregation"
    final_output_ = cast(ChatOutput, final_output)
    final_output_["output"] = model_response
    return final_output_


class ChatService:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        agent: Agent[None, str],
        # agent: Agent[Dep, AnswerStruct],
    ):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.agent = agent
        self.logger = logger

    def _store_ehr_and_result(
        self,
        user_id: str,
        query: str,
        result: ChatOutput,
    ):
        pass

    async def chat_stream(
        self, user_id: str, query: str
    ) -> AsyncGenerator[StreamEvent]:
        i = 0
        yield {
            "event": StreamEventType.conversation_start,
            "data": {
                "conversation_id": "thisisaplaceholder",
            },
        }
        async for event in self.agent.run_stream_events(query):
            self.logger.debug("Got new event", new_event=event)
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
                            if i < 2:
                                data["citation"] = {
                                    "start_index": 0,
                                    "end_index": 1,
                                    "title": "Test reference",
                                    "src": "http://localhost:8000/",
                                    "reference_type": ReferenceType.webpage,
                                    "content": "This is a place holder content",
                                }
                                i += 1
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
                    self.logger.debug("Got final result")
                    usage = event.result.usage()
                    result: StreamEvent_FinalResult = {
                        "event": StreamEventType.final_result,
                        "data": {
                            "conversation_id": "thisisaplaceholder",
                            "id": "thisisaplaceholder",
                            "status": ResponseStatus.completed,
                            "output": None,
                            "usage": {
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                            },
                        },
                    }
                    yield result
                    self.logger.debug("Result", result=result)
                    result_ = cast(ChatOutput, result)
                    result_["output"] = _convert_to_ours(
                        event.result.new_messages(), self.logger
                    )
                    self._store_ehr_and_result(user_id, query, result_)
                case _:
                    pass

    async def chat(self, user_id: str, query: str) -> ChatOutput:
        run = await self.agent.run(query)
        usage = run.usage()
        messages = _convert_to_ours(run.new_messages(), self.logger)

        result: ChatOutput = {
            "conversation_id": "thisisaplaceholder",
            "id": "thisisaplaceholder",
            "status": ResponseStatus.completed,
            "output": messages,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
        }
        return result


def _convert_to_ours(
    msgs: Sequence[ModelRequest | ModelResponse], logger: BoundLogger
):
    messages: list[ModelResponseContent] = []
    for message in msgs:
        parts = message.parts
        for part in parts:
            match part.part_kind:
                case "thinking":
                    if part.has_content():
                        messages.append(
                            {
                                "type": ModelResponse_ContentType.thinking,
                                "content": part.content,
                            }
                        )
                case "text":
                    if part.has_content():
                        messages.append(
                            {
                                "type": ModelResponse_ContentType.text,
                                "content": part.content,
                                "citations": [],
                            }
                        )
                case "tool-call" | "builtin-tool-call":
                    messages.append(
                        {
                            "type": ModelResponse_ContentType.builtin_tool_call,
                            "tool_call_id": part.tool_call_id,
                            "hinted_tool_name": part.tool_name,
                            "hinted_args": part.args_as_json_str(),
                        }
                    )
                case "tool-return" | "builtin-tool-return":
                    messages.append(
                        {
                            "type": ModelResponse_ContentType.builtin_tool_result,
                            "tool_call_id": part.tool_call_id,
                            "hinted_result": None,
                        }
                    )
                case _:
                    logger.warn("Unprocessed part", part=part)
                    pass
    return messages
