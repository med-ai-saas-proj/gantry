from ..models import Message

from abc import ABC, abstractmethod


class Serializer[T](ABC):
    """Abstract base class for serializers that convert between conversation messages and a specific format."""

    @abstractmethod
    async def serializeConversationMessages(
        self, conversation_id: int, msg: T
    ) -> Message:
        pass

    @abstractmethod
    async def deserializeConversationMessages(
        self, message: Message, project_id: int
    ) -> T:
        pass
