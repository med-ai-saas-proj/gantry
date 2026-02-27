from src.shared.custom_types.error_exception import RecoverableError

from .types import FileType, FileUploadInfo
from ..agent.dtos.model import (
    AudioInput,
    ImageInput,
    ModelInput,
    VideoInput,
    AudioURLInput,
    DocumentInput,
    ImageURLInput,
    VideoURLInput,
    DocumentURLInput,
)
from ..agent.stream_handler import StreamHandler
from ..file_storage.services import (
    FileStorageService,
    FileNotFoundInSystemError,
)

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
from safe_result import Ok, Err, Result


DATA_URL_BASE64_RE = re.compile(
    r"^data:([a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)$"
)


class InvalidDataUrlError(RecoverableError):
    """Raised when an invalid data URL is encountered."""

    status = 400
    code = "invalid_data_url"
    title = "Invalid data URL"
    detail = "Data URL must be in the format data:<mime_type>;base64,<data>"


class InvalidBase64ContentError(RecoverableError):
    """Raised when invalid base64 content is encountered."""

    status = 400
    code = "invalid_base64_content"
    title = "Invalid base64 content"
    detail = "Base64 content is invalid or cannot be decoded"


class ConversationSession:
    """Manages the state of a conversation session, including message history and file uploads."""

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
        project_id: int,
    ):
        self.stream_handler = stream_handler
        self.mess_history = mess_history
        self.file_service = file_service
        self.file_upload_map = {}
        self.file_upload_queue = asyncio.Queue()
        self.project_id = project_id

    def getMessageHistory(self) -> Sequence[ModelMessage]:
        return self.mess_history

    def getStreamHandler(self) -> StreamHandler:
        return self.stream_handler

    def extractFileContentFromUrl(
        self, data_url: str
    ) -> Result[
        tuple[str, bytes], InvalidDataUrlError | InvalidBase64ContentError
    ]:
        """Extract file content from base64 data URL."""
        match = DATA_URL_BASE64_RE.match(data_url)
        if not match:
            return Err(InvalidDataUrlError())

        mime_type = match.group(1)
        b64_data = match.group(2)

        try:
            content_bytes = base64.b64decode(b64_data, validate=True)
        except Exception:
            return Err(InvalidBase64ContentError())
        return Ok((mime_type, content_bytes))

    async def addUploadFile(
        self,
        file_data: bytes,
        mime_type: str,
    ) -> uuid.UUID:
        """Upload file and return file ID."""
        file_id = uuid.uuid4()
        file_info = FileUploadInfo(
            file_id=file_id,
            file_data=file_data,
            mime_type=mime_type,
            is_uploaded=False,
        )
        self.file_upload_map[file_id] = file_info
        await self.file_upload_queue.put(file_info)
        return file_id

    async def userInputToPydanticAI(
        self, input: ModelInput
    ) -> Result[Sequence[UserContent], FileNotFoundInSystemError]:
        """Convert user input to Pydantic AI UserContent format and handle file uploads."""
        model_input: list[UserContent] = []
        if isinstance(input, str):
            model_input = [input]
        elif isinstance(input, Sequence):
            model_input = []
            for message in input:
                if isinstance(message, str):
                    model_input.append(message)
                elif isinstance(message, ImageInput):
                    root_message = message.root
                    if isinstance(root_message, ImageURLInput):
                        result = self.extractFileContentFromUrl(root_message.url)
                        if result.is_ok():
                            mime_type, file_data = result.unwrap()
                            file_id = await self.addUploadFile(
                                file_data, mime_type
                            )
                            content = BinaryContent.from_data_uri(root_message.url)
                            content.vendor_metadata = {
                                "file_id": file_id,
                                "is_uploading": True,
                                "file_type": FileType.IMAGE,
                            }
                        else:
                            # If not data URL, assume it's a direct URL
                            content = ImageUrl(url=root_message.url)
                    else:
                        _res = await self.file_service.get_file_metadata_and_url(
                            root_message.file_id, self.project_id
                        )
                        if isinstance(_res, Err):
                            return _res
                        file_url, metadata = _res.unwrap()
                        content = ImageUrl(
                            url=file_url,
                            vendor_metadata={
                            "file_id": root_message.file_id,
                            "file_type": FileType.IMAGE,
                        })
                    model_input.append(content)
                elif isinstance(message, AudioInput):
                    root_message = message.root
                    if isinstance(root_message, AudioURLInput):
                        res = self.extractFileContentFromUrl(root_message.url)
                        if res.is_ok():
                            mime_type, file_data = res.unwrap()
                            file_id = await self.addUploadFile(
                                file_data, mime_type
                            )
                            content = BinaryContent.from_data_uri(root_message.url)
                            content.vendor_metadata = {
                                "file_id": file_id,
                                "is_uploading": True,
                                "file_type": FileType.AUDIO,
                            }
                        else:
                            # If not data URL, assume it's a direct URL
                            content = AudioUrl(url=root_message.url)
                    else:
                        _res = await self.file_service.get_file_metadata_and_url(
                            root_message.file_id, self.project_id
                        )
                        if isinstance(_res, Err):
                            return _res
                        file_url, metadata = _res.unwrap()
                        content = AudioUrl(
                            url=file_url,
                            vendor_metadata={
                            "file_id": root_message.file_id,
                            "file_type": FileType.AUDIO,
                        })
                    model_input.append(content)
                elif isinstance(message, VideoInput):
                    root_message = message.root
                    if isinstance(root_message, VideoURLInput):
                        res = self.extractFileContentFromUrl(root_message.url)
                        if res.is_ok():
                            mime_type, file_data = res.unwrap()
                            file_id = await self.addUploadFile(
                                file_data, mime_type
                            )
                            content = BinaryContent.from_data_uri(root_message.url)
                            content.vendor_metadata = {
                                "file_id": file_id,
                                "is_uploading": True,
                                "file_type": FileType.VIDEO,
                            }
                        else:
                            # If not data URL, assume it's a direct URL
                            content = VideoUrl(url=root_message.url)
                    else:
                        _res = await self.file_service.get_file_metadata_and_url(
                            root_message.file_id, self.project_id
                        )
                        if isinstance(_res, Err):
                            return _res
                        file_url, metadata = _res.unwrap()
                        content = VideoUrl(
                            url=file_url,
                            vendor_metadata={
                            "file_id": root_message.file_id,
                            "file_type": FileType.VIDEO,
                        })
                    model_input.append(content)
                elif isinstance(message, DocumentInput):
                    root_message = message.root
                    if isinstance(root_message, DocumentURLInput):
                        res = self.extractFileContentFromUrl(root_message.url)
                        if res.is_ok():
                            mime_type, file_data = res.unwrap()
                            file_id = await self.addUploadFile(
                                file_data, mime_type
                            )
                            content = BinaryContent.from_data_uri(root_message.url)
                            content.vendor_metadata = {
                                "file_id": file_id,
                                "is_uploading": True,
                                "file_type": FileType.DOCUMENT,
                            }
                        else:
                            # If not data URL, assume it's a direct URL
                            content = DocumentUrl(
                                url=root_message.url, media_type=root_message.mime_type
                            )
                    else:
                        _res = await self.file_service.get_file_metadata_and_url(
                            root_message.file_id, self.project_id
                        )
                        if isinstance(_res, Err):
                            return _res
                        file_url, metadata = _res.unwrap()
                        content = DocumentUrl(
                            url=file_url,
                            media_type=metadata["mime_type"],
                            vendor_metadata={
                                "file_id": root_message.file_id,
                                "file_type": FileType.DOCUMENT,
                            },
                        )
                    model_input.append(content)
                else:
                    pass
        return Ok(model_input)
