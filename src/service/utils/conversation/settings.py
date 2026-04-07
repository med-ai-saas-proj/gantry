from src.settings import AppSettings, ModifiedBaseSettings


@AppSettings.register("conversation")
class ConversationSettings(ModifiedBaseSettings):
    """Settings for file storage configuration."""

    cache_ttl: int = 600  # in seconds
    cache_limit: int = 50


def getConversationSettings():
    """Get conversation settings from environment variables."""
    return ConversationSettings.get()
