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

import uuid
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
        conversion_manager: ConversationManager,
    ):
        self.agent = agent
        self.logger = logger
        self.models_service = models_service
        self.conversion_manager = conversion_manager

    async def chatStream(
        self,
        api_key_info: ApiKeyInfo,
        model_id: str,
        query: ModelInput,
        conversation_uid: uuid.UUID | None = None,
    ) -> AsyncGenerator[StreamEvent]:
        model, model_config = self.models_service.get_model(model_id)
        async with self.conversion_manager.startConversion(
            conversation_uid,
            api_key_info,
        ) as conversation:
            model_input = (
                await conversation.userInputToPydanticAI(query)
            ).unwrap()
            async for event in conversation.convertSSEStream(
                self.agent.run_stream_events(
                    model_input,
                    model=model,
                    message_history=conversation.mess_history,
                    deps=constructChatAgentDeps(api_key_info, model_config),
                )
            ):
                try:
                    yield event
                except Exception as e:
                    # current version pydantic ai not supported cancel
                    print("Error yielding event", e)

    async def chat(
        self,
        api_key_info: ApiKeyInfo,
        model_id: str,
        query: ModelInput,
        conversation_uid: uuid.UUID | None = None,
    ) -> ChatOutput:
        result = await aggregateStream(
            self.chatStream(api_key_info, model_id, query, conversation_uid)
        )
        return result
