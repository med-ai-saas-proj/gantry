from src.services.postgres import PostgresService
from src.utils.dict_utils import DictUtils
from src.agents.shared_types import AnswerStruct
from src.custom_types.ehr import EHRDict, PrescriptionDict
from src.custom_types.responses import SSEResponse
from src.dtos.ehr import InputPrescription, InputEHR

import asyncio

from typing import (
    Callable,
    TypedDict,
    Any,
    Union,
    AsyncIterable,
    Optional,
    Literal,
)
from enum import Enum
from contextlib import _GeneratorContextManager
from functools import partial

from structlog.stdlib import BoundLogger
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
)

from pydantic import ValidationError


class Event(str, Enum):
    delta = "delta"
    done = "done"
    tool_call = "tool_call"
    tool_done = "tool_done"
    think_delta = "think_delta"


class Delta(TypedDict):
    d: str


class Done(TypedDict):
    d: Literal[""]


class ThinkDelta(TypedDict):
    t_d: Optional[str]


class ToolCall(TypedDict):
    tool_call_id: str
    tool_name: str
    args: dict[str, Any]


class ToolResult(TypedDict):
    tool_call_id: str
    result: Union[str, list, dict]


DataType = Union[ToolCall, ToolResult, Delta, ThinkDelta]
# SSEContent = SSEResponse.Content[Event, DataType]


class StreamDelta(TypedDict):
    event: Literal[Event.delta]
    data: Delta


class StreamDone(TypedDict):
    event: Literal[Event.done]
    data: Done


class StreamThinkDelta(TypedDict):
    event: Literal[Event.think_delta]
    data: ThinkDelta


class StreamToolCall(TypedDict):
    event: Literal[Event.tool_call]
    data: ToolCall


class StreamToolResult(TypedDict):
    event: Literal[Event.tool_done]
    data: ToolResult


SSEContent = Union[
    StreamDelta, StreamThinkDelta, StreamToolCall, StreamToolResult, StreamDone
]


class UsedTool(TypedDict):
    tool_call_id: str
    tool_name: str
    args: dict[str, Any]
    result: Union[str, list, dict]


class Answer(TypedDict):
    output: str
    reasoning: Optional[str]
    used_tools: list[UsedTool]


AQueue = asyncio.Queue[SSEContent]


class AISearchService:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        agent: Agent[None, AnswerStruct],
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
        ctx: RunContext,
        event_stream: AsyncIterable[AgentStreamEvent],
        queue: AQueue,
    ):
        async for event in event_stream:
            to_put: Optional[SSEContent] = None
            if isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    to_put = {
                        "event": Event.delta,
                        "data": {"d": event.delta.content_delta},
                    }
                elif isinstance(event.delta, ThinkingPartDelta):
                    to_put = {
                        "event": Event.think_delta,
                        "data": {"t_d": event.delta.content_delta},
                    }
            elif isinstance(event, FunctionToolCallEvent):
                to_put = {
                    "event": Event.tool_call,
                    "data": {
                        "tool_call_id": event.tool_call_id,
                        "tool_name": event.part.tool_name,
                        "args": event.part.args_as_dict(),
                    },
                }
            elif isinstance(event, FunctionToolResultEvent):
                to_put = {
                    "event": Event.tool_done,
                    "data": {
                        "tool_call_id": event.tool_call_id,
                        "result": event.result.content,
                    },
                }
            if to_put is not None:
                await queue.put(to_put)

    async def _generate_advice_stream(
        self,
        user_id: str,
        query: str,
        queue: AQueue,
    ):
        agent_result = ""
        try:
            async with self.agent.run_stream(
                query,
                event_stream_handler=partial(
                    self.event_stream_handler, queue=queue
                ),
            ) as run:
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
                        {"event": Event.delta, "data": {"d": new_response}}
                    )
                    # yield new_response
                    agent_result = answer
                await queue.put({"event": Event.done, "data": {"d": ""}})
        except Exception as e:
            self.logger.error(__file__, error=e)
            result = {"result": agent_result, "error": str(e)}
            raise e
        finally:
            result = {"result": agent_result}
            self.logger.debug("Result", result=result)
            self._store_ehr_and_result(user_id, query, result)
            queue.shutdown()

    async def generate_advice_stream(self, user_id: str, query: str):
        queue = AQueue()
        generate_advice_task = asyncio.ensure_future(
            self._generate_advice_stream(user_id, query, queue)
        )
        while True:
            try:
                it = await queue.get()
                yield it
                if it["event"] == Event.done:
                    break
            except:
                break
            queue.task_done()

        # await queue.join()

    async def generate_advice(self, user_id: str, query: str) -> Answer:
        # Why does this instead of run_sync?
        # Anthropic said: non-streaming Messages API requests are not expected to exceed a 10 minute timeout
        # https://docs.anthropic.com/en/api/errors#long-requests
        res = ""
        thought = ""
        used_tools: dict[str, UsedTool] = {}
        # async queue.get():
        async for output in self.generate_advice_stream(user_id, query):
            match output["event"]:
                case Event.done:
                    break
                case Event.delta:
                    res += output["data"]["d"]
                case Event.think_delta:
                    thought += output["data"]["t_d"] or ""
                case Event.tool_call:
                    used_tools[output["data"]["tool_call_id"]] = {
                        **output["data"],
                        "result": {},
                    }
                case Event.tool_done:
                    used_tools[output["data"]["tool_call_id"]]["result"] = (
                        output["data"]["result"]
                    )
        return {
            "output": res,
            "used_tools": list(used_tools.values()),
            "reasoning": thought if thought else None,
        }
