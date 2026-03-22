from src.shared.custom_types.error_exception import UnrecoverableError

from enum import Enum
from typing import Any, TypedDict, NotRequired

from pydantic import SecretStr
from pyrusult import Ok, Err, Result
from pydantic_ai import ModelSettings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_ai.models import Model, infer_model
from pydantic_ai.providers import infer_provider_class


class ModelConfig(TypedDict):
    name: str
    api_key: NotRequired[SecretStr]
    args: NotRequired[dict[str, Any]]
    settings: NotRequired[ModelSettings]


class AvailableModels(str, Enum):
    BigModel = "BigModel"
    MediumModel = "MediumModel"
    SmallModel = "SmallModel"
    OcrModel = "OcrModel"


class ModelsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="models_", case_sensitive=False
    )

    configs: dict[AvailableModels, ModelConfig]


def createModel(config: ModelConfig) -> Model:
    model = infer_model(
        config["name"],
        provider_factory=lambda provider_name: infer_provider_class(
            provider_name
        )(
            api_key=(config["api_key"].get_secret_value())
            if "api_key" in config
            else None,
            **config.get("args", {}),
        ),
    )
    model._settings = config.get("settings")
    return model


models_settings = ModelsSettings()
available_models: dict[AvailableModels, Model] = {
    name: createModel(config)
    for name, config in models_settings.configs.items()
}


class ModelNotFoundError(UnrecoverableError):
    detail = "Can't find model in config"


def getModel(name: AvailableModels) -> Result[Model, ModelNotFoundError]:
    try:
        return Ok(available_models[name])
    except Exception as e:
        return Err(ModelNotFoundError(e))


# big_model = GroqModel(
#     "openai/gpt-oss-20b",
#     provider=GroqProvider(api_key=GROQ_API_KEY),
#     settings={
#         "max_tokens": 32000,
#         "parallel_tool_calls": True,
#         "extra_body": {
#             "reasoning_effort": "low",
#         },
#     },
# )

# medium_model = GroqModel(
#     "openai/gpt-oss-20b",
#     provider=GroqProvider(api_key=GROQ_API_KEY),
#     settings={
#         "max_tokens": 32000,
#         "parallel_tool_calls": True,
#         "extra_body": {
#             "reasoning_effort": "low",
#         },
#     },
# )

# small_model = GroqModel(
#     "openai/gpt-oss-20b",
#     provider=GroqProvider(api_key=GROQ_API_KEY),
#     settings={
#         "max_tokens": 32000,
#         "parallel_tool_calls": True,
#         "extra_body": {
#             "reasoning_effort": "low",
#         },
#     },
# )


# from pydantic_ai.models.anthropic import AnthropicModel
# from pydantic_ai.providers.anthropic import AnthropicProvider


# big_model = AnthropicModel(
#     "claude-4-opus-20250514",
#     provider=AnthropicProvider(api_key=env_const.ANTHROPIC_API_KEY),
#     settings={"max_tokens": 32000, "parallel_tool_calls": True},
# )

# medium_model = AnthropicModel(
#     "claude-4-sonnet-20250514",
#     provider=AnthropicProvider(api_key=env_const.ANTHROPIC_API_KEY),
#     settings={"max_tokens": 32000, "parallel_tool_calls": True},
# )

# small_model = AnthropicModel(
#     "claude-4-sonnet-20250514",
#     provider=AnthropicProvider(api_key=env_const.ANTHROPIC_API_KEY),
#     settings={"max_tokens": 32000, "parallel_tool_calls": True},
# )
