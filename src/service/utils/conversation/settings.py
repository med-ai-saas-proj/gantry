from pydantic_settings import BaseSettings


class ConversationSettings(BaseSettings):
    """Settings for file storage configuration."""

    model_config = {
        "env_prefix": "conversation_",
        "case_sensitive": False,
    }
    cache_ttl: int = 600 # in seconds
    cache_limit: int = 50


def getConversationSettings() -> ConversationSettings:
    """Get conversation settings from environment variables."""
    return ConversationSettings()
