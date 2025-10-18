from src.chat import dtos as chat_dtos
from src.shared.consts import messages_const
from src.db.postgres.service import PostgresService
from src.shared.agents.shared_types import AnswerStruct
from src.shared.dtos.generation_output import (
    ResponseStatus,
    GenerationOutput,
)

from .agents import Dep

import json
import asyncio
from typing import (
    Any,
    Callable,
    AsyncIterable,
    AsyncGenerator,
    cast,
)
from functools import partial
from contextlib import _GeneratorContextManager

from pydantic import ValidationError
from pydantic_ai import Agent, RunContext
from structlog.stdlib import BoundLogger
from pydantic_ai.messages import (
    AgentStreamEvent,
)


AQueue = asyncio.Queue[chat_dtos.StreamEvent]


async def aggregate_stream(
    stream: AsyncGenerator[chat_dtos.StreamEvent],
) -> chat_dtos.ChatOutput:
    # Why does this instead of run_sync?
    # Anthropic said: non-streaming Messages API requests are not expected
    # to exceed a 10 minute timeout
    # https://docs.anthropic.com/en/api/errors#long-requests

    final_output: GenerationOutput[None] | None = None
    model_response: list[chat_dtos.ModelResponseContent] = []
    last_part: chat_dtos.ModelResponseContent | None = None

    async for output in stream:
        match output["event"]:
            case chat_dtos.StreamEventType.conversation_start:
                pass
            case chat_dtos.StreamEventType.part_start:
                part_start_data = output["data"]
                if last_part:
                    model_response.append(last_part)
                    last_part = None
                match part_start_data:
                    case chat_dtos.StreamEvent_PartType.output:
                        last_part = {
                            "type": chat_dtos.ModelResponse_ContentType.text,
                            "content": "",
                            "citations": [],
                        }
                    case chat_dtos.StreamEvent_PartType.thinking:
                        last_part = {
                            "type": chat_dtos.ModelResponse_ContentType.thinking,
                            "content": None,
                        }
                    case chat_dtos.StreamEvent_PartType.builtin_tool_call:
                        last_part = {
                            "type": chat_dtos.ModelResponse_ContentType.builtin_tool_call,
                            "tool_call_id": "",
                            "hinted_tool_name": None,
                            "hinted_args": None,
                        }
                    case chat_dtos.StreamEvent_PartType.builtin_tool_result:
                        last_part = {
                            "type": chat_dtos.ModelResponse_ContentType.builtin_tool_result,
                            "tool_call_id": "",
                            "hinted_result": None,
                        }
                    case _:
                        last_part = None
            case chat_dtos.StreamEventType.part_delta:
                part_delta_data = output["data"]
                assert last_part is not None, (
                    "Check ai search stream aggregation"
                )
                match part_delta_data["type"]:
                    case chat_dtos.StreamEvent_PartType.output:
                        assert (
                            last_part["type"]
                            == chat_dtos.ModelResponse_ContentType.text
                        )
                        last_part["content"] += part_delta_data["delta"] or ""
                        if part_delta_data["citation"]:
                            last_part["citations"].append(
                                part_delta_data["citation"]
                            )
                    case chat_dtos.StreamEvent_PartType.thinking:
                        assert (
                            last_part["type"]
                            == chat_dtos.ModelResponse_ContentType.thinking
                        )
                        if part_delta_data["delta"]:
                            if last_part["content"] is None:
                                last_part["content"] = ""
                            last_part["content"] += part_delta_data["delta"]
                    case chat_dtos.StreamEvent_PartType.builtin_tool_call:
                        assert (
                            last_part["type"]
                            == chat_dtos.ModelResponse_ContentType.builtin_tool_call
                        )
                        last_part["tool_call_id"] = part_delta_data[
                            "tool_call_id"
                        ]
                        last_part["hinted_tool_name"] = part_delta_data[
                            "hinted_tool_name"
                        ]
                        last_part["hinted_args"] = part_delta_data[
                            "hinted_args"
                        ]
                    case chat_dtos.StreamEvent_PartType.builtin_tool_result:
                        assert (
                            last_part["type"]
                            == chat_dtos.ModelResponse_ContentType.builtin_tool_result
                        )
                        last_part["tool_call_id"] = part_delta_data[
                            "tool_call_id"
                        ]
                        last_part["hinted_result"] = part_delta_data[
                            "hinted_result"
                        ]
                    case _:
                        pass
            case chat_dtos.StreamEventType.final_result:
                final_output = output["data"]

    assert final_output is not None, "Check ai search stream aggregation"
    final_output_ = cast(chat_dtos.ChatOutput, final_output)
    final_output_["output"] = model_response
    return final_output_


class AISearchService:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        agent: Agent[Dep, AnswerStruct],
    ):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.agent = agent
        self.logger = logger

    def _store_ehr_and_result(
        self,
        user_id: str,
        query: str,
        result: dict,
    ):
        pass

    async def event_stream_handler(
        self,
        ctx: RunContext[Dep],
        event_stream: AsyncIterable[AgentStreamEvent],
        queue: AQueue,
    ):
        async for event in event_stream:
            self.logger.debug("Got new event", new_event=event)
            to_put: chat_dtos.StreamEvent | None = None
            match event.event_kind:
                case "part_start":
                    part_start_data: chat_dtos.StreamEvent_PartType = (
                        chat_dtos.StreamEvent_PartType.output
                    )
                    match event.part.part_kind:
                        case "text":
                            part_start_data = (
                                chat_dtos.StreamEvent_PartType.output
                            )
                        case "thinking":
                            part_start_data = (
                                chat_dtos.StreamEvent_PartType.thinking
                            )
                        case "tool-call":
                            part_start_data = (
                                chat_dtos.StreamEvent_PartType.builtin_tool_call
                            )
                        case "builtin-tool-call":
                            part_start_data = (
                                chat_dtos.StreamEvent_PartType.builtin_tool_call
                            )
                        case "builtin-tool-return":
                            part_start_data = chat_dtos.StreamEvent_PartType.builtin_tool_result
                        case _:
                            part_start_data = None

                    if part_start_data:
                        to_put = {
                            "event": chat_dtos.StreamEventType.part_start,
                            "data": part_start_data,
                        }
                case "part_delta":
                    part_delta_data: (
                        chat_dtos.StreamEvent_PartDeltaData | None
                    ) = None
                    delta = event.delta
                    match delta.part_delta_kind:
                        case "text":
                            part_delta_data = {
                                "type": chat_dtos.StreamEvent_PartType.output,
                                "delta": delta.content_delta,
                                "citation": None,
                            }
                        case "thinking":
                            part_delta_data = {
                                "type": chat_dtos.StreamEvent_PartType.thinking,
                                "delta": delta.content_delta,
                            }
                        case "tool_call":
                            part_delta_data = None
                        case _:
                            part_delta_data = None
                    if part_delta_data:
                        to_put = {
                            "event": chat_dtos.StreamEventType.part_delta,
                            "data": part_delta_data,
                        }
                case "function_tool_call":
                    to_put = {
                        "event": chat_dtos.StreamEventType.part_delta,
                        "data": {
                            "type": chat_dtos.StreamEvent_PartType.builtin_tool_call,
                            "tool_call_id": event.part.tool_call_id,
                            "hinted_tool_name": event.part.tool_name,
                            "hinted_args": event.part.args_as_json_str(),
                        },
                    }
                case "function_tool_result":
                    # Put part start to signify the end of last part
                    await queue.put(
                        {
                            "event": chat_dtos.StreamEventType.part_start,
                            "data": chat_dtos.StreamEvent_PartType.builtin_tool_result,
                        }
                    )
                    to_put = {
                        "event": chat_dtos.StreamEventType.part_delta,
                        "data": {
                            "type": chat_dtos.StreamEvent_PartType.builtin_tool_result,
                            "tool_call_id": event.result.tool_call_id,
                            "hinted_result": json.dumps(
                                event.result.content, ensure_ascii=False
                            ),
                        },
                    }
                case "builtin_tool_call":
                    to_put = {
                        "event": chat_dtos.StreamEventType.part_delta,
                        "data": {
                            "type": chat_dtos.StreamEvent_PartType.builtin_tool_call,
                            "tool_call_id": event.part.tool_call_id,
                            "hinted_tool_name": event.part.tool_name,
                            "hinted_args": event.part.args_as_json_str(),
                        },
                    }
                case "builtin_tool_result":
                    to_put = {
                        "event": chat_dtos.StreamEventType.part_delta,
                        "data": {
                            "type": chat_dtos.StreamEvent_PartType.builtin_tool_result,
                            "tool_call_id": event.result.tool_call_id,
                            "hinted_result": json.dumps(
                                event.result.content, ensure_ascii=False
                            ),
                        },
                    }
                case "final_result":
                    self.logger.debug("Got final result")
                    pass
                case _:
                    pass
            if to_put is not None:
                self.logger.debug("to_put", to_put=to_put)
                await queue.put(to_put)

    async def _ai_search_stream(
        self,
        user_id: str,
        query: str,
        queue: AQueue,
    ):
        agent_result = ""
        self.logger.debug("Ai search is running")
        await queue.put(
            {
                "event": chat_dtos.StreamEventType.conversation_start,
                "data": {
                    "conversation_id": "placeholdervalue",
                    "message_id": "placeholdervalue",
                },
            }
        )
        self.logger.debug("Ai search is running 2")
        async with self.agent.run_stream(
            query,
            deps={"viewed_urls": []},
            event_stream_handler=partial(
                self.event_stream_handler, queue=queue
            ),
        ) as run:
            self.logger.debug("Ai search is running loop")
            try:
                i = 0
                async for output, end in run.stream_responses():
                    try:
                        validated_output = await run.validate_response_output(
                            output,
                            allow_partial=not end,
                        )
                    except ValidationError:
                        continue
                    answer = validated_output["answer"]
                    new_response = answer[len(agent_result) :]
                    await queue.put(
                        {
                            "event": chat_dtos.StreamEventType.part_delta,
                            "data": {
                                "type": chat_dtos.StreamEvent_PartType.output,
                                "delta": new_response,
                                "citation": {
                                    "start_index": 0,
                                    "end_index": 1,
                                    "title": "Test reference",
                                    "src": "http://localhost:8000/",
                                    "reference_type": chat_dtos.ReferenceType.webpage,
                                    "content": "This is a place holder content",
                                }
                                if i < 2
                                else None,
                            },
                        }
                    )
                    i += 1
                    # yield new_response
                    agent_result = answer
                usage = run.usage()
                await queue.put(
                    {
                        "event": chat_dtos.StreamEventType.final_result,
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
                )

            except Exception as e:
                usage = run.usage()
                await queue.put(
                    {
                        "event": chat_dtos.StreamEventType.final_result,
                        "data": {
                            "conversation_id": "thisisaplaceholder",
                            "id": "thisisaplaceholder",
                            "status": ResponseStatus.error,
                            "error": {
                                "code": "500",
                                "message": messages_const.INTERNAL_SERVER_ERROR,
                            },
                            "output": None,
                            "usage": {
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                            },
                        },
                    }
                )
                self.logger.error("Internal server error", error=e)
                result = {"result": agent_result, "error": str(e)}
                raise e
            finally:
                result = {"result": agent_result}
                self.logger.debug("Result", result=result)
                self._store_ehr_and_result(user_id, query, result)
                queue.shutdown()

    async def ai_search_stream(
        self, user_id: str, query: str
    ) -> AsyncGenerator[chat_dtos.StreamEvent]:
        queue = AQueue()
        generate_advice_task = asyncio.ensure_future(
            self._ai_search_stream(user_id, query, queue)
        )
        while True:
            try:
                it = await queue.get()
                self.logger.debug("Got new output", it=it)
                yield it
                if it["event"] == chat_dtos.StreamEventType.final_result:
                    break
            except:
                break
            queue.task_done()

        # await queue.join()

    async def ai_search(self, user_id: str, query: str) -> chat_dtos.ChatOutput:
        return await aggregate_stream(self.ai_search_stream(user_id, query))
