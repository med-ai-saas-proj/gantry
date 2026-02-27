from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.conversation.types import FileUploadInfo
from src.service.utils.file_storage.utils import detect_file_type
from src.service.utils.agent.stream_handler import StreamHandler
from src.service.utils.conversation.services import ConversationService
from src.service.utils.file_storage.services import FileStorageService
from src.service.utils.conversation.conversation_session import (
    ConversationSession,
)

import uuid
import asyncio
import mimetypes
from typing import Sequence
from asyncio import QueueShutDown
from contextlib import asynccontextmanager

from aioredlock import Aioredlock
from pydantic_ai import ModelMessage


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
            ).unwrap()
        else:
            conversation_uid = str(uuid.uuid4())

        async with await self.redis_lock_manager.lock(
            f"conversation:{conversation_uid}"
        ) as lock:
            mess_history: Sequence[ModelMessage] = []

            if conversation_id:
                mess_history = (
                    await self.conversation_service.get_conversation_message(
                        conversation_id, conversation_uid
                    )
                )

            stream_handler = StreamHandler(
                conversation_id=conversation_id,
                conversation_uid=conversation_uid,
            )

            conversation_session = ConversationSession(
                stream_handler=stream_handler,
                mess_history=mess_history,
                file_service=self.file_service,
            )

            file_upload_task = asyncio.create_task(
                self.fileUploadWorker(
                    conversation_session.file_upload_map,
                    conversation_session.file_upload_queue,
                )
            )
            try:
                yield conversation_session
            except Exception as e:
                print(f"An error occurred during conversion: {e}")
                raise e
            finally:
                new_message = stream_handler.new_messages
                conversation_session.file_upload_queue.shutdown()
                await file_upload_task

                if new_message:
                    await self.conversation_service.store_conversation(
                        conversation_id,
                        conversation_uid,
                        api_key_info["project_id"],
                        new_message,
                    )
                pass

    async def fileUploadWorker(
        self,
        file_upload_map: dict[uuid.UUID, FileUploadInfo],
        file_upload_queue: asyncio.Queue[FileUploadInfo],
    ):
        while True:
            try:
                file_info = await file_upload_queue.get()
                await self.fileUpload(file_info)
                file_upload_map[file_info["file_id"]]["is_uploaded"] = True
            except QueueShutDown:
                break
            except Exception as e:
                print(f"Error uploading file: {e}")

    async def fileUpload(self, file_info: FileUploadInfo):
        file_data = file_info["file_data"]
        if file_info["mime_type"]:
            mime_type = file_info["mime_type"]
            ext = mimetypes.guess_extension(mime_type)
            if ext:
                ext = ext.lstrip(".")  # Remove leading dot
        else:
            mime_type, ext = detect_file_type(file_data)
        await self.file_service.upload_file(
            file_name=f"uploaded_file.{ext}",
            file_data=file_data,
            file_size=len(file_data),
            mime_type=mime_type,
            ext=ext,
            file_id=file_info["file_id"],
        )
