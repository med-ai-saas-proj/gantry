from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.file_storage.utils import detect_file_type
from src.service.utils.file_storage.services import FileStorageService

from .types import FileUploadInfo
from .services import ConversationService
from .conversation_session import (
    ConversationSession,
)

import uuid
import asyncio
import mimetypes
from typing import Sequence
from asyncio import QueueShutDown
from contextlib import asynccontextmanager

from pydantic_ai import ModelMessage
from redis.asyncio import Redis
from structlog.stdlib import BoundLogger


class ConversationManager:
    def __init__(
        self,
        logger: BoundLogger,
        redis_client: Redis,
        conversation_service: ConversationService,
        file_service: FileStorageService,
    ):
        self.logger = logger
        self.redis_client = redis_client
        self.conversation_service = conversation_service
        self.file_service = file_service

    @asynccontextmanager
    async def startConversion(
        self,
        conversation_uid: uuid.UUID | None,
        api_key_info: ApiKeyInfo,
        message_context_window: int = 20,
    ):
        conversation_id: int | None = None
        if conversation_uid is not None:
            metadata = (
                await self.conversation_service.getConversationMetadata(
                    conversation_uid, api_key_info["project_id"]
                )
            ).unwrap()
            conversation_id = metadata["conversation_id"]
        else:
            conversation_uid = uuid.uuid4()

        async with self.redis_client.lock(
            f"conversation:{conversation_uid}"
        ) as lock:
            mess_history: Sequence[ModelMessage] = []

            if conversation_id:
                mess_history = await self.conversation_service.getAndDeserializeConversationMessages(
                    conversation_id,
                    conversation_uid,
                    api_key_info["project_id"],
                    message_context_window,
                )

            conversation_session = ConversationSession(
                mess_history=mess_history,
                file_service=self.file_service,
                conversation_uid=conversation_uid,
                project_id=api_key_info["project_id"],
            )

            file_upload_task = asyncio.create_task(
                self.fileUploadWorker(
                    project_id=api_key_info["project_id"],
                    file_upload_map=conversation_session.file_upload_map,
                    file_upload_queue=conversation_session.file_upload_queue,
                )
            )
            try:
                yield conversation_session
            except Exception as e:
                self.logger.warn("Errro yielding event", {"exception": e})
                raise e
            finally:
                new_message = conversation_session.new_messages
                conversation_session.file_upload_queue.shutdown()
                await file_upload_task

                if new_message:
                    await self.conversation_service.serializeAndStoreConversationMessages(
                        conversation_id,
                        conversation_uid,
                        api_key_info["project_id"],
                        new_message,
                    )
                pass

    async def fileUploadWorker(
        self,
        project_id: int,
        file_upload_map: dict[uuid.UUID, FileUploadInfo],
        file_upload_queue: asyncio.Queue[FileUploadInfo],
    ):
        while True:
            try:
                file_info = await file_upload_queue.get()
                await self.fileUpload(file_info, project_id)
                file_upload_map[file_info["file_id"]]["is_uploaded"] = True
            except QueueShutDown:
                break
            except Exception as e:
                print(f"Error uploading file: {e}")

    async def fileUpload(self, file_info: FileUploadInfo, project_id: int):
        file_data = file_info["file_data"]
        if file_info["mime_type"]:
            mime_type = file_info["mime_type"]
            ext = mimetypes.guess_extension(mime_type)
            if ext:
                ext = ext.lstrip(".")  # Remove leading dot
        else:
            mime_type, ext = detect_file_type(file_data)
        await self.file_service.uploadFile(
            file_name=f"uploaded_file.{ext}",
            file_data=file_data,
            file_size=len(file_data),
            mime_type=mime_type,
            project_id=project_id,
            ext=ext,
            file_uid=file_info["file_id"],
        )
