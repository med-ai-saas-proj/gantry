from pydantic_settings import BaseSettings


class ConversationSettings(BaseSettings):
    """Settings for file storage configuration."""

    cache_ttl: int = 600  # in seconds
    cache_limit: int = 50
