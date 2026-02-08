from src.db.base import BaseSQLModel
from src.db.utils import WithID, WithUUID, WithCreateUpdateTimestamp

import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column


class FileStorageBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "FileStorage"}

class FileType(enum.Enum):
    """Enum-like class for file types."""
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    GENERAL = "general"


class File(
    WithCreateUpdateTimestamp, WithID, WithUUID, FileStorageBaseSQLModel
):
    """Represents a file associated with messages in conversations."""

    __tablename__ = "Files"

    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    filepath: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_in_bytes: Mapped[int] = mapped_column(nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType), nullable=False, default=FileType.GENERAL
    )
