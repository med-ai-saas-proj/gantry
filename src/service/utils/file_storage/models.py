from src.db.base import BaseSQLModel
from src.db.utils import (
    WithID,
    WithClientUUID,
    WithCreateUpdateTimestamp,
)
from src.management.projects.models import Project

import enum

from sqlalchemy import Enum, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey


class FileStorageBaseSQLModel(BaseSQLModel):
    """Base SQL Model for this module only."""

    __abstract__ = True
    __table_args__ = {"schema": "FileStorage"}


class FileStatus(enum.Enum):
    """Enum-like class for file statuses."""

    UPLOADING = "uploading"
    AVAILABLE = "available"
    DELETED = "deleted"


class File(
    WithCreateUpdateTimestamp, WithID, WithClientUUID, FileStorageBaseSQLModel
):
    """Represents a file associated with messages in conversations."""

    __tablename__ = "Files"

    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    filepath: Mapped[str] = mapped_column(String(512), nullable=False)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Project.id, ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_in_bytes: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus),
        nullable=False,
        default=FileStatus.UPLOADING,
        init=False,
    )
