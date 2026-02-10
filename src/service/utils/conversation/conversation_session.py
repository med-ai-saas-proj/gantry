from src.service.utils.file_storage.utils import (
    detect_file_type,
)
from src.service.utils.file_storage.models import FileType
from src.service.utils.agent.stream_handler import StreamHandler

from ..agent.dtos.model import (
    AudioURL as InputAudioURL,
    FileLink,
    ImageURL as InputImageURL,
    VideoURL as InputVideoURL,
    ModelInput,
    DocumentURL as InputDocumentURL,
)
from ..file_storage.services import FileStorageService

import uuid
import base64
from typing import (
    Sequence,
)

from pydantic_ai import (
    AudioUrl,
    ImageUrl,
    VideoUrl,
    DocumentUrl,
    UserContent,
    ModelMessage,
)


class ConversationSession:
    stream_handler: StreamHandler
    mess_history: Sequence[ModelMessage]
    file_service: FileStorageService

    def __init__(
        self,
        stream_handler: StreamHandler,
        mess_history: Sequence[ModelMessage],
        file_service: FileStorageService,
    ):
        self.stream_handler = stream_handler
        self.mess_history = mess_history
        self.file_service = file_service

    def getMessageHistory(self) -> Sequence[ModelMessage]:
        return self.mess_history

    def getStreamHandler(self) -> StreamHandler:
        return self.stream_handler

    def extractFileContentFromUrl(self, url: str) -> bytes | None:
        """Extract file content from data URL."""
        prefix = "data:"
        if url.startswith(prefix):
            comma_index = url.find(",")
            if comma_index != -1:
                # mine_type = url[len(prefix) : comma_index]
                content = url[comma_index + 1 :]
                return base64.b64decode(content)
        return None

    async def uploadFile(
        self, file_data: bytes, file_type: FileType
    ) -> uuid.UUID:
        """Upload file and return file ID."""
        mine_type, ext = detect_file_type(file_data)
        return await self.file_service.upload_file(
            "uploaded_image",
            file_data=file_data,
            file_size=len(file_data),
            mime_type=mine_type,
            file_type=file_type,
            ext=ext,
        )

    async def userInputToPydanticAI(
        self, input: ModelInput
    ) -> Sequence[UserContent]:
        model_input: list[UserContent] = []
        if isinstance(input, str):
            model_input = [input]
        elif isinstance(input, Sequence):
            model_input = []
            for message in input:
                if isinstance(message, str):
                    model_input.append(message)
                elif isinstance(message, InputImageURL):
                    file_data = self.extractFileContentFromUrl(message.url)
                    if file_data:
                        file_id = await self.uploadFile(
                            file_data, FileType.IMAGE
                        )
                        file_url = await self.file_service.get_file_url(file_id)
                        model_input.append(
                            ImageUrl(
                                url=file_url,
                                vendor_metadata={"file_id": file_id},
                            )
                        )
                    else:
                        # If not data URL, assume it's a direct URL
                        model_input.append(ImageUrl(url=message.url))
                elif isinstance(message, InputAudioURL):
                    file_data = self.extractFileContentFromUrl(message.url)
                    if file_data:
                        file_id = await self.uploadFile(
                            file_data, FileType.AUDIO
                        )
                        file_url = await self.file_service.get_file_url(file_id)
                        model_input.append(
                            AudioUrl(
                                url=file_url,
                                vendor_metadata={"file_id": file_id},
                            )
                        )
                    else:
                        # If not data URL, assume it's a direct URL
                        model_input.append(AudioUrl(url=message.url))
                elif isinstance(message, InputVideoURL):
                    file_data = self.extractFileContentFromUrl(message.url)
                    if file_data:
                        file_id = await self.uploadFile(
                            file_data, FileType.VIDEO
                        )
                        file_url = await self.file_service.get_file_url(file_id)
                        model_input.append(
                            VideoUrl(
                                url=file_url,
                                vendor_metadata={"file_id": file_id},
                            )
                        )
                    else:
                        # If not data URL, assume it's a direct URL
                        model_input.append(VideoUrl(url=message.url))
                elif isinstance(message, InputDocumentURL):
                    file_data = self.extractFileContentFromUrl(message.url)
                    if file_data:
                        file_id = await self.uploadFile(
                            file_data, FileType.DOCUMENT
                        )
                        file_url = await self.file_service.get_file_url(file_id)
                        model_input.append(
                            DocumentUrl(
                                url=file_url,
                                vendor_metadata={"file_id": file_id},
                            )
                        )
                    else:
                        # If not data URL, assume it's a direct URL
                        model_input.append(DocumentUrl(url=message.url))
                elif isinstance(message, FileLink):
                    (
                        file_url,
                        metadata,
                    ) = await self.file_service.get_file_metadata_and_url(
                        message.file_id
                    )
                    if metadata["file_type"] == FileType.IMAGE:
                        model_input.append(
                            ImageUrl(
                                url=file_url,
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                    elif metadata["file_type"] == FileType.AUDIO:
                        model_input.append(
                            AudioUrl(
                                url=file_url,
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                    elif metadata["file_type"] == FileType.VIDEO:
                        model_input.append(
                            VideoUrl(
                                url=file_url,
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                    else:
                        model_input.append(
                            DocumentUrl(
                                url=file_url,
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                else:
                    raise ValueError("Not supported type of user input")
        return model_input
