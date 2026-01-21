"""Chat service."""

from .agents import constructChatAgentDeps
from ..utils.agent.stream import (
    aggregateStream,
    convertAgentStream,
    userInputToPydanticAI,
)
from ..utils.agent.agent_deps import AgentDeps
from ..utils.agent.dtos.model import ChatOutput, ModelInput, StreamEvent
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.models.models_service import ModelsService

from typing import AsyncGenerator

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class ChatService:
    def __init__(
        self,
        session_scope,
        logger: BoundLogger,
        agent: Agent[AgentDeps, str],
        # agent: Agent[Dep, AnswerStruct],
        models_service: ModelsService,
    ):
        self.agent = agent
        self.logger = logger
        self.models_service = models_service

    def _store_ehr_and_result(
        self,
        user_id: str,
        query: ModelInput,
        result: ChatOutput,
    ):
        pass

    async def chatStream(
        self, api_key_info: ApiKeyInfo, model_id: str, query: ModelInput
    ) -> AsyncGenerator[StreamEvent]:
        model, model_config = self.models_service.get_model(model_id)

        model_input = userInputToPydanticAI(query)

        async for event in convertAgentStream(
            self.agent.run_stream_events(
                model_input,
                model=model,
                deps=constructChatAgentDeps(api_key_info, model_config),
            )
        ):
            yield event

    async def chat(
        self, api_key_info: ApiKeyInfo, model_id: str, query: ModelInput
    ) -> ChatOutput:
        result = await aggregateStream(
            self.chatStream(api_key_info, model_id, query)
        )
        return result
