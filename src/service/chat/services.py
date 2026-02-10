"""Chat service."""

from .agents import constructChatAgentDeps
from ..utils.agent.stream import (
    aggregateStream,
)
from ..utils.agent.agent_deps import AgentDeps
from ..utils.agent.dtos.model import ChatOutput, ModelInput, StreamEvent
from ..utils.models.models_service import ModelsService
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.conversation.conversation_manager import ConversationManager

from typing import AsyncGenerator

from pydantic_ai import Agent
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger


class ChatService:
    def __init__(
        self,
        session_scope,
        logger: BoundLogger,
        agent: Agent[AgentDeps, str],
        # agent: Agent[Dep, AnswerStruct],
        models_service: ModelsService,
        conversion_manager: ConversationManager,
        redis: Redis,
    ):
        self.agent = agent
        self.logger = logger
        self.models_service = models_service
        self.conversion_manager = conversion_manager
        self.redis = redis

    def _store_ehr_and_result(
        self,
        user_id: str,
        query: ModelInput,
        result: ChatOutput,
    ):
        pass

    async def chatStream(
        self,
        api_key_info: ApiKeyInfo,
        model_id: str,
        query: ModelInput,
        conversation_uid: str | None = None,
    ) -> AsyncGenerator[StreamEvent]:
        model, model_config = self.models_service.get_model(model_id)
        async with self.conversion_manager.startConversion(
            conversation_uid,
            api_key_info,
        ) as conversation:
            model_input = await conversation.userInputToPydanticAI(query)
            async for event in conversation.stream_handler.convertAgentStream(
                self.agent.run_stream_events(
                    model_input,
                    model=model,
                    message_history=conversation.mess_history,
                    deps=constructChatAgentDeps(api_key_info, model_config),
                )
            ):
                yield event

    async def chat(
        self,
        api_key_info: ApiKeyInfo,
        model_id: str,
        query: ModelInput,
        conversation_uid: str | None = None,
    ) -> ChatOutput:
        result = await aggregateStream(
            self.chatStream(api_key_info, model_id, query, conversation_uid)
        )
        return result
