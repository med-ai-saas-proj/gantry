from src.settings import AppSettings, ModifiedBaseSettings


@AppSettings.register("aimodel")
class ModelsSettings(ModifiedBaseSettings):
    openai_base_url: str | None = None
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


def getModelsSettings():
    return ModelsSettings()
