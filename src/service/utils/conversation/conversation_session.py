from src.service.utils.file_storage.models import FileType
from src.service.utils.agent.stream_handler import StreamHandler

from .types import FileUploadInfo
from ..agent.dtos.model import (
    AudioURL as InputAudioURL,
    FileLink,
    ImageURL as InputImageURL,
    VideoURL as InputVideoURL,
    ModelInput,
    DocumentURL as InputDocumentURL,
)
from ..file_storage.services import FileStorageService

import re
import uuid
import base64
import asyncio
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
    BinaryContent,
)


DATA_URL_BASE64_RE = re.compile(
    r"^data:([a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)$"
)


class ConversationSession:
    stream_handler: StreamHandler
    mess_history: Sequence[ModelMessage]
    file_service: FileStorageService
    file_upload_queue: asyncio.Queue[FileUploadInfo]
    file_upload_map: dict[uuid.UUID, FileUploadInfo] = {}

    def __init__(
        self,
        stream_handler: StreamHandler,
        mess_history: Sequence[ModelMessage],
        file_service: FileStorageService,
    ):
        self.stream_handler = stream_handler
        self.mess_history = mess_history
        self.file_service = file_service
        self.file_upload_map = {}
        self.file_upload_queue = asyncio.Queue()

    def getMessageHistory(self) -> Sequence[ModelMessage]:
        return self.mess_history

    def getStreamHandler(self) -> StreamHandler:
        return self.stream_handler

    def extractFileContentFromUrl(self, data_url: str) -> tuple[str, bytes]:
        """Extract file content from base64 data URL."""
        match = DATA_URL_BASE64_RE.match(data_url)
        if not match:
            raise ValueError(
                "Invalid base64 data URL, format must be data:<mime_type>;base64,<data>"
            )

        mime_type = match.group(1)
        b64_data = match.group(2)

        try:
            content_bytes = base64.b64decode(b64_data, validate=True)
        except Exception as e:
            raise ValueError("Invalid base64 content") from e
        return mime_type, content_bytes

    async def addUploadFile(
        self,
        file_data: bytes,
        file_type: FileType,
        mime_type: str,
    ) -> uuid.UUID:
        """Upload file and return file ID."""
        file_id = uuid.uuid4()
        file_info = FileUploadInfo(
            file_id=file_id,
            file_data=file_data,
            file_type=file_type,
            mime_type=mime_type,
            is_uploaded=False,
        )
        self.file_upload_map[file_id] = file_info
        await self.file_upload_queue.put(file_info)
        return file_id

    async def userInputToPydanticAI(
        self, input: ModelInput
    ) -> Sequence[UserContent]:
        """Convert user input to Pydantic AI UserContent format and handle file uploads."""
        model_input: list[UserContent] = []
        if isinstance(input, str):
            model_input = [input]
        elif isinstance(input, Sequence):
            model_input = []
            for message in input:
                if isinstance(message, str):
                    model_input.append(message)
                elif isinstance(message, InputImageURL):
                    try:
                        mime_type, file_data = self.extractFileContentFromUrl(
                            message.url
                        )
                        file_id = await self.addUploadFile(
                            file_data, FileType.IMAGE, mime_type
                        )
                        content = BinaryContent.from_data_uri(message.url)
                        content.vendor_metadata = {
                            "file_id": file_id,
                            "is_uploading": True,
                        }
                        model_input.append(content)
                    except ValueError:
                        # If not data URL, assume it's a direct URL
                        model_input.append(ImageUrl(url=message.url))

                elif isinstance(message, InputAudioURL):
                    try:
                        mime_type, file_data = self.extractFileContentFromUrl(
                            message.url
                        )
                        file_id = await self.addUploadFile(
                            file_data, FileType.AUDIO, mime_type
                        )
                        content = BinaryContent.from_data_uri(message.url)
                        content.vendor_metadata = {
                            "file_id": file_id,
                            "is_uploading": True,
                        }
                        model_input.append(content)
                    except ValueError:
                        # If not data URL, assume it's a direct URL
                        model_input.append(AudioUrl(url=message.url))
                elif isinstance(message, InputVideoURL):
                    try:
                        mime_type, file_data = self.extractFileContentFromUrl(
                            message.url
                        )
                        file_id = await self.addUploadFile(
                            file_data, FileType.VIDEO, mime_type
                        )
                        content = BinaryContent.from_data_uri(message.url)
                        content.vendor_metadata = {
                            "file_id": file_id,
                            "is_uploading": True,
                        }
                        model_input.append(content)
                    except ValueError:
                        # If not data URL, assume it's a direct URL
                        model_input.append(VideoUrl(url=message.url))
                elif isinstance(message, InputDocumentURL):
                    try:
                        mime_type, file_data = self.extractFileContentFromUrl(
                            message.url
                        )
                        file_id = await self.addUploadFile(
                            file_data, FileType.DOCUMENT, mime_type
                        )
                        content = BinaryContent.from_data_uri(message.url)
                        content.vendor_metadata = {
                            "file_id": file_id,
                            "is_uploading": True,
                        }
                        model_input.append(content)
                    except ValueError:
                        # If not data URL, assume it's a direct URL
                        model_input.append(
                            DocumentUrl(
                                url=message.url, media_type=message.mime_type
                            )
                        )
                elif isinstance(message, FileLink):
                    (
                        file_url,
                        metadata,
                    ) = await self.file_service.get_file_metadata_and_url(
                        message.file_id
                    )
                    print(
                        f"Fetched file URL: {file_url} with metadata: {metadata}"
                    )
                    if metadata["file_type"] == FileType.IMAGE:
                        model_input.append(
                            ImageUrl(
                                url=file_url,
                                media_type=metadata["mime_type"],
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                    elif metadata["file_type"] == FileType.AUDIO:
                        model_input.append(
                            AudioUrl(
                                url=file_url,
                                media_type=metadata["mime_type"],
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                    elif metadata["file_type"] == FileType.VIDEO:
                        model_input.append(
                            VideoUrl(
                                url=file_url,
                                media_type=metadata["mime_type"],
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                    else:
                        model_input.append(
                            DocumentUrl(
                                url=file_url,
                                media_type=metadata["mime_type"],
                                vendor_metadata={"file_id": message.file_id},
                            )
                        )
                else:
                    raise ValueError("Not supported type of user input")
        return model_input
