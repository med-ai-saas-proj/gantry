from src.db.postgres.service import PostgresService
from src.shared.agents.shared_types import AnswerStruct
from src.shared.dtos.generation_output import Usage


from .dtos import Answer
from .agents import Dep

import asyncio
from enum import Enum
from typing import (
    Any,
    Union,
    Literal,
    Callable,
    Optional,
    TypedDict,
    NotRequired,
    AsyncIterable,
)
from functools import partial
from contextlib import _GeneratorContextManager

from pydantic import ValidationError
from pydantic_ai import Agent, RunContext
from structlog.stdlib import BoundLogger
from pydantic_ai.messages import (
    AgentStreamEvent,
)

# Suppose to be like typescript's partial, but python doesn't have that
# can use dict, but I want type hint
PartialAnswer = Answer
AQueue = asyncio.Queue[PartialAnswer | Usage | None]


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
            to_put: PartialAnswer | None = None
            if event.event_kind == "part_delta":
                if event.delta.part_delta_kind == "text":
                    to_put = {"result": event.delta.content_delta}
                elif event.delta.part_delta_kind == "thinking":
                    to_put = {"reasoning": event.delta.content_delta or ""}
            elif event.event_kind == "function_tool_call":
                # to_put = {}
                # to_put = {
                #     "event": Event.tool_call,
                #     "data": {
                #         "tool_call_id": event.tool_call_id,
                #         "tool_name": event.part.tool_name,
                #         "args": event.part.args_as_dict(),
                #     },
                # }
                pass
            elif event.event_kind == "function_tool_result":
                to_put = {"viewed_pages": ctx.deps["viewed_urls"]}
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
                deps={"viewed_urls": []},
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
                    await queue.put({"result": new_response})
                    # yield new_response
                    agent_result = answer
                usage = run.usage()
                await queue.put(
                    {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                    }
                )

            await queue.put(None)
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
                if it is None:
                    break
                yield it
            except:
                break
            queue.task_done()

        # await queue.join()

    async def generate_advice(
        self, user_id: str, query: str
    ) -> tuple[Answer, Usage]:
        # Why does this instead of run_sync?
        # Anthropic said: non-streaming Messages API requests are not expected
        # to exceed a 10 minute timeout
        # https://docs.anthropic.com/en/api/errors#long-requests
        final_result: Answer = {
            "reasoning": None,
            "result": "",
            "citations": [],
            "viewed_pages": [],
        }
        usage: Usage = {"input_tokens": 0, "output_tokens": 0}
        # async queue.get():
        async for output in self.generate_advice_stream(user_id, query):
            for key, value in output.items():
                if key in final_result:
                    if final_result[key] is None:
                        final_result[key] = ""
                    final_result[key] += value
                else:
                    assert key in usage, "Check this out"
                    usage[key] = value

        return final_result, usage
