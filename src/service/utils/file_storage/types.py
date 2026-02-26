from typing import TypedDict
from datetime import datetime


class FileRecord(TypedDict):
    """Representation of a file record in storage."""

    id: str
    filename: str
    mime_type: str
    size: int
    storage_path: str
    created_at: datetime
