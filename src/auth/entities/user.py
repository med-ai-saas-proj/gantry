from src.shared.entities.base import BaseEntity

from typing import NotRequired
from datetime import datetime


class User(BaseEntity):
    id: NotRequired[str]
    email: NotRequired[str]
    password: NotRequired[str]
    createdAt: NotRequired[datetime]
    updated_at: NotRequired[datetime]
