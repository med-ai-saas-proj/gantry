from datetime import datetime
from typing import TypedDict


class FileRecord(TypedDict):
    """Representation of a file record in storage."""

    id: str
    filename: str
    content_type: str
    size: int
    storage_path: str
    created_at: datetime
