import traceback
from uuid import UUID
from typing import Any
from datetime import date, datetime

from pydantic import BaseModel


def json_serializer(obj: Any):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Exception):
        return traceback.format_exception(obj)
    raise TypeError(f"Type {type(obj)} not serializable")
