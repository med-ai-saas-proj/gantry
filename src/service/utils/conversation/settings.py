from src.settings import AppSettings, ConversationSettings


def getConversationSettings() -> ConversationSettings:
    return AppSettings.get().conversation
