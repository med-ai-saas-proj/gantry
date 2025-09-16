from typing import Any, NotRequired
from src.entities.base import BaseEntity
from datetime import datetime


class User(BaseEntity):
    id: NotRequired[str]
    email: NotRequired[str]
    password: NotRequired[str]
    createdAt: NotRequired[datetime]
    updated_at: NotRequired[datetime]
