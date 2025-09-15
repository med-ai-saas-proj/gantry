from typing import Any, NotRequired
from src.entities.base import BaseEntity


class PredefinedQuestion(BaseEntity):
    id: NotRequired[Any]
    question: NotRequired[Any]
    questionEmbedding: NotRequired[Any]
    answer: NotRequired[Any]
    referenceText: NotRequired[Any]
    createdAt: NotRequired[Any]
