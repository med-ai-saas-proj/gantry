from datetime import datetime, date
from typing import Any


def json_serializer(obj: Any):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")