"""Chat service."""
from .agents import constructChatAgentDeps
from ..utils.agent.stream import (
    aggregateStream,
    convertAgentStream,
    userInputToPydanticAI,
)
from ..utils.agent.agent_deps import AgentDeps
from ..utils.agent.dtos.model import ChatOutput, ModelInput, StreamEvent
from ..utils.conversation.services import ConversationService
from ..utils.models.models_service import ModelsService
from ...management.api_keys.entities import ApiKeyInfo

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
        conversion_service: ConversationService
    ):
        self.agent = agent
        self.logger = logger
        self.models_service = models_service
        self.conversation_service = conversion_service

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
        conversation_uid: str | None = None
    ) -> AsyncGenerator[StreamEvent]:
        model, model_config = self.models_service.get_model(model_id)
        conversation_id: int | None = None
        if conversation_uid:
            conversation_id = await self.conversation_service.get_conversation_id(
                conversation_uid, api_key_info
            )
        else:
            conversation_uid = str(uuid.uuid4())

        print("conversation_id", conversation_id)
        mess_history = await self.conversation_service.get_conversation_message(
            conversation_id,
            conversation_uid
        ) if conversation_id else []

        model_input = userInputToPydanticAI(query)
        async for event in convertAgentStream(
            self.agent.run_stream_events(
                model_input,
                model=model,
                message_history=mess_history,
                deps=constructChatAgentDeps(api_key_info, model_config),
            ),
            conversation_id=conversation_id,
            conversation_uid=conversation_uid,
            api_key_info=api_key_info,
            conversation_service=self.conversation_service,
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
