from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings


class ConversationSettings(BaseSettings):
    cache_ttl: Annotated[
        int,
        Field(description="Conversation cache TTL in seconds."),
    ] = 600
    cache_limit: Annotated[
        int,
        Field(
            description="Maximum number of cached conversations per user.",
        ),
    ] = 50
