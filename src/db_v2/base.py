from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Column, func, MetaData

metadata = MetaData(schema="app")

def timestamps() -> list[Column]:
    return [
        Column(
            "created_at",
            DateTime,
            nullable=False,
            default=func.now()
        ),
        Column(
            "updated_at",
            DateTime,
            nullable=False,
            default=func.now(),
            onupdate=func.now()
        )
    ]


class TableColumns:
    __key__ = "id"


@dataclass(kw_only=True)
class BaseEntity:
    __key__ = "id"

@dataclass(kw_only=True)
class TimestampsFields:
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
