from typing import Any, NotRequired
from src.entities.base import BaseEntity


class RegulationReference(BaseEntity):
    id: NotRequired[Any]
    questionId: NotRequired[Any]
    regulationId: NotRequired[Any]
    createdAt: NotRequired[Any]
