from uuid import UUID
from typing import TypedDict
from datetime import datetime


class FileRecord(TypedDict):
    """Representation of a file record in storage."""

    uid: UUID
    filename: str
    mime_type: str
    size: int
    storage_path: str
    created_at: datetime
    extra_metadata: dict | None
