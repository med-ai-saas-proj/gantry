from src.settings import AppSettings

from pydantic_settings import BaseSettings


@AppSettings.register("conversation")
class ConversationSettings(BaseSettings):
    """Settings for file storage configuration."""

    cache_ttl: int = 600  # in seconds
    cache_limit: int = 50


def getConversationSettings() -> ConversationSettings:
    """Get conversation settings from environment variables."""
    return ConversationSettings()
