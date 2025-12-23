from src.shared.agents.agent_manager import AgentManagerService

import asyncio
import contextlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Union, Literal, Optional, TypedDict, AsyncIterable
from functools import partial

from pydantic import BaseModel
from pydantic_ai import (
    Agent,
    RunContext,
    PartEndEvent,
    PartDeltaEvent,
    PartStartEvent,
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
)
from pydantic_core import ValidationError
from structlog.stdlib import BoundLogger
from pydantic_ai.messages import (
    TextPartDelta,
    ThinkingPartDelta,
)


class Event(Enum):
    """Events that can be emitted by the agent service."""

    delta = "delta"
    done = "done"
    tool_call = "tool_call"
    tool_done = "tool_done"
    think_delta = "think_delta"


class Delta(TypedDict):
    """Represents a delta update from the agent service."""

    d: str


class Done(TypedDict):
    """Represents the completion of an action by the agent service."""

    d: Literal[""]


class ThinkDelta(TypedDict):
    """Represents a thinking delta update from the agent service."""

    t_d: Optional[str]


class ToolCall(TypedDict):
    """Represents a tool call made by the agent service."""

    tool_call_id: str
    tool_name: str
    args: dict[str, Any]


class ToolResult(TypedDict):
    """Represents the result of a tool call."""

    tool_call_id: str
    result: Union[str, list, dict]


DataType = Union[ToolCall, ToolResult, Delta, ThinkDelta]


class StreamDelta(TypedDict):
    """Represents a delta event in the stream."""

    event: Literal[Event.delta]
    data: Delta


class StreamDone(TypedDict):
    """Represents a done event in the stream."""

    event: Literal[Event.done]
    data: Done


class StreamThinkDelta(TypedDict):
    """Represents a think delta event in the stream."""

    event: Literal[Event.think_delta]
    data: ThinkDelta


class StreamToolCall(TypedDict):
    """Represents a tool call event in the stream."""

    event: Literal[Event.tool_call]
    data: ToolCall


class StreamToolResult(TypedDict):
    """Represents a tool result event in the stream."""

    event: Literal[Event.tool_done]
    data: ToolResult


SSEContent = Union[
    StreamDelta, StreamThinkDelta, StreamToolCall, StreamToolResult, StreamDone
]

AQueue = asyncio.Queue[SSEContent]


class AgentService[InputType: BaseModel, AgentResultType: BaseModel](ABC):
    """Abstract base class for agent services."""

    def __init__(self, logger: BoundLogger, agent_manager: AgentManagerService):
        """Initializes the AgentService with the given AgentManagerService."""
        self.agent_manager = agent_manager
        self.logger = logger

    @abstractmethod
    async def initialize_agent(self) -> Agent[Any, AgentResultType]:
        """Initializes and returns an agent instance."""
        pass

    @abstractmethod
    async def preprocess_input(self, input: InputType) -> str:
        """Preprocesses the input before passing it to the agent."""
        pass

    @abstractmethod
    async def store_result(
        self,
        user_id: str,
        input: InputType,
        result: AgentResultType | None,
    ):
        """Stores the result of the agent's processing."""
        pass

    async def _eventStreamHandler(
        self,
        ctx: RunContext,
        event_stream: AsyncIterable[AgentStreamEvent],
        queue: AQueue,
    ):
        """Handles the event stream from the agent and puts relevant events into the queue."""
        try:
            async for event in event_stream:
                to_put: Optional[SSEContent] = None
                if isinstance(event, PartDeltaEvent):
                    if isinstance(event.delta, TextPartDelta):
                        to_put = StreamDelta(
                            event=Event.delta,
                            data={"d": event.delta.content_delta},
                        )
                    elif isinstance(event.delta, ThinkingPartDelta):
                        to_put = StreamThinkDelta(
                            event=Event.think_delta,
                            data={"t_d": event.delta.content_delta},
                        )
                elif isinstance(event, FunctionToolCallEvent):
                    to_put = StreamToolCall(
                        event=Event.tool_call,
                        data={
                            "tool_call_id": event.tool_call_id,
                            "tool_name": event.part.tool_name,
                            "args": event.part.args_as_dict(),
                        },
                    )
                elif isinstance(event, FunctionToolResultEvent):
                    to_put = StreamToolResult(
                        event=Event.tool_done,
                        data={
                            "tool_call_id": event.tool_call_id,
                            "result": event.result.content,
                        },
                    )
                if to_put is not None:
                    await queue.put(to_put)
        except asyncio.QueueShutDown:
            self.logger.debug("Queue shutdown, stop event handler")
        except asyncio.CancelledError:
            self.logger.debug("Event handler cancelled")
            raise

    async def _generateStream(
        self,
        user_id: str,
        queue: AQueue,
        agent: Agent[Any, AgentResultType],
        input: InputType,
    ):
        """Generates the agent response stream and puts events into the queue."""
        agent_result: AgentResultType | None = None
        processed_input = await self.preprocess_input(input)
        result = {}
        try:
            async with agent.run_stream(
                processed_input,
                event_stream_handler=partial(
                    self._eventStreamHandler, queue=queue
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
                    agent_result = validated_output
                result = {"result": agent_result}
                await queue.put(StreamDone(event=Event.done, data={"d": ""}))
        except asyncio.CancelledError:
            self.logger.info("Stream cancelled by client")
            result = {
                "result": agent_result,
                "error": "Stream cancelled by client",
            }
            raise
        except Exception as e:
            self.logger.error(__file__, error=e)
            result = {"result": agent_result, "error": str(e)}
            raise
        finally:
            self.logger.debug("Result", result=result)
            await self.store_result(user_id, input, agent_result)
            queue.shutdown()

    async def generate_agent_response(
        self,
        user_id: str,
        input: InputType,
    ) -> AsyncIterable[SSEContent]:
        """Generates agent responses as an async iterable of SSEContent."""
        queue: AQueue = asyncio.Queue()

        agent = await self.initialize_agent()

        task = asyncio.create_task(
            self._generateStream(user_id, queue, agent, input)
        )

        try:
            while True:
                try:
                    it = await queue.get()
                    yield it
                except asyncio.QueueShutDown:
                    break  # queue is shutdown
        except asyncio.CancelledError:
            raise  # client disconnected
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
