"""This file contain definition of chat's services."""

from src.service.utils.agent.agent_deps import AgentDeps

from .agents import constructAiSearchAgentDeps
from ..utils.agent.stream import (
    aggregateStream,
    convertAgentStream,
    userInputToPydanticAI,
)
from ..utils.agent.dtos.model import ChatOutput, ModelInput, StreamEvent

from typing import AsyncGenerator

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class AiSearchService:
    def __init__(
        self,
        session_scope,
        logger: BoundLogger,
        agent: Agent[AgentDeps, str],
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

    async def aiSearchStream(
        self, user_id: str, query: ModelInput
    ) -> AsyncGenerator[StreamEvent]:
        model_input = userInputToPydanticAI(query)

        async for event in convertAgentStream(
            self.agent.run_stream_events(
                model_input,
                deps=constructAiSearchAgentDeps(
                    {
                        "user_id": user_id  # todo update later
                    }
                ),
            )
        ):
            yield event

    async def aiSearch(self, user_id: str, query: ModelInput) -> ChatOutput:
        result = await aggregateStream(self.aiSearchStream(user_id, query))
        return result
