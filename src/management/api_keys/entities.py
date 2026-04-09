from typing import TypedDict


class ApiKeyInfo(TypedDict):
    """Represents information about an API key."""

    api_key_id: int
    user_id: str
    project_id: int
    org_id: str
    project_uid: str
    hashed_key: str
