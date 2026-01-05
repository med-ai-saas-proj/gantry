"""This file contain definition of chat's services."""

from ..utils.agent.stream import (
    aggregateStream,
    convertAgentStream,
    userInputToPydanticAI,
)
from ..utils.agent.dtos.model import ChatOutput, ModelInput, StreamEvent

from typing import AsyncGenerator

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class ChatService:
    def __init__(
        self,
        session_scope,
        logger: BoundLogger,
        agent: Agent[None, str],
        # agent: Agent[Dep, AnswerStruct],
    ):
        self.agent = agent
        self.logger = logger

    def _store_ehr_and_result(
        self,
        user_id: str,
        query: ModelInput,
        result: ChatOutput,
    ):
        pass

    async def chatStream(
        self, user_id: str, query: ModelInput
    ) -> AsyncGenerator[StreamEvent]:
        model_input = userInputToPydanticAI(query)

        async for event in convertAgentStream(
            self.agent.run_stream_events(model_input)
        ):
            yield event

    async def chat(self, user_id: str, query: ModelInput) -> ChatOutput:
        result = await aggregateStream(self.chat_stream(user_id, query))
        return result
