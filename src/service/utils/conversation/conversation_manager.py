import uuid
from contextlib import asynccontextmanager
from typing import Sequence

from aioredlock import Aioredlock
from pydantic_ai import ModelMessage

from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.agent.stream_handler import StreamHandler
from src.service.utils.conversation.conversation_session import (
    ConversationSession,
)
from src.service.utils.conversation.services import ConversationService
from src.service.utils.file_storage.services import FileStorageService


class ConversationManager:
    def __init__(
        self,
        conversation_service: ConversationService,
        redis_lock_manager: Aioredlock,
        file_service: FileStorageService,
    ):
        self.conversation_service = conversation_service
        self.redis_lock_manager = redis_lock_manager
        self.file_service = file_service

    @asynccontextmanager
    async def startConversion(
        self,
        conversation_uid: str | None,
        api_key_info: ApiKeyInfo,
    ):
        conversation_id: int | None = None
        if conversation_uid:
            conversation_id = (
                await self.conversation_service.get_conversation_id(
                    conversation_uid, api_key_info
                )
            )
        else:
            conversation_uid = str(uuid.uuid4())

        async with await self.redis_lock_manager.lock(
            f"conversation:{conversation_uid}", lock_timeout=10
        ) as lock:
            mess_history: Sequence[ModelMessage] = []

            if conversation_id:
                mess_history = (
                    await self.conversation_service.get_conversation_message(
                        conversation_id, conversation_uid
                    )
                )

            stream_handler = StreamHandler(
                file_service=self.file_service,
                conversation_id=conversation_id,
                conversation_uid=conversation_uid,
                api_key_info=api_key_info,
                conversation_service=self.conversation_service,
            )
            try:
                yield ConversationSession(
                    stream_handler=stream_handler,
                    mess_history=mess_history,
                )
            except Exception as e:
                print(f"An error occurred during conversion: {e}")
            finally:
                new_message = stream_handler.new_messages
                if new_message:
                    await self.conversation_service.store_conversation(
                        conversation_id,
                        conversation_uid,
                        api_key_info["project_id"],
                        new_message,
                    )
                pass
