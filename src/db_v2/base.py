from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import Column, DateTime, MetaData, func


metadata = MetaData(schema="app")


def timestamps() -> list[Column]:
    return [
        Column("created_at", DateTime, nullable=False, default=func.now()),
        Column(
            "updated_at",
            DateTime,
            nullable=False,
            default=func.now(),
            onupdate=func.now(),
        ),
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
