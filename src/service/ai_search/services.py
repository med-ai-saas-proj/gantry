"""AI Search Service."""

from src.service.utils.conversation.conversation_manager import (
    ConversationManager,
)

from .agents import constructAiSearchAgentDeps
from ..utils.agent.stream import (
    aggregateStream,
)
from ..utils.agent.agent_deps import AgentDeps
from ..utils.agent.dtos.model import ChatOutput, ModelInput, StreamEvent
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.models.models_service import ModelsService

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
        models_service: ModelsService,
        conversion_manager: ConversationManager,
    ):
        self.agent = agent
        self.logger = logger
        self.models_service = models_service
        self.conversion_manager = conversion_manager

    def _store_ehr_and_result(
        self,
        user_id: str,
        query: ModelInput,
        result: ChatOutput,
    ):
        pass

    async def aiSearchStream(
        self, api_key_info: ApiKeyInfo, model_id: str, query: ModelInput
    ) -> AsyncGenerator[StreamEvent]:
        model, model_config = self.models_service.get_model(model_id)
        async with self.conversion_manager.startConversion(
            None,
            api_key_info,
        ) as conversation:
            model_input = (
                await conversation.userInputToPydanticAI(query)
            ).unwrap()
            async for event in conversation.convertSSEStream(
                self.agent.run_stream_events(
                    model_input,
                    model=model,
                    deps=constructAiSearchAgentDeps(api_key_info, model_config),
                )
            ):
                try:
                    yield event
                except Exception as e:
                    # current version pydantic ai not supported cancel
                    pass

    async def aiSearch(
        self, api_key_info: ApiKeyInfo, model_id: str, query: ModelInput
    ) -> ChatOutput:
        result = await aggregateStream(
            self.aiSearchStream(api_key_info, model_id, query)
        )
        return result
