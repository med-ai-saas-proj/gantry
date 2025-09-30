from src.shared.entities.base import BaseEntity

from typing import NotRequired
from datetime import datetime


class ApiKey(BaseEntity):
    id: NotRequired[str]
    user_id: NotRequired[str]
    api_key: NotRequired[str]
    name: NotRequired[str]
    is_active: NotRequired[bool]
    last_used_at: NotRequired[datetime]
    expires_at: NotRequired[datetime]
    created_at: NotRequired[datetime]
    updated_at: NotRequired[datetime]
