from gantry.settings import AppSettings, ConversationSettings


def getConversationSettings() -> ConversationSettings:
    return AppSettings.get().conversation
