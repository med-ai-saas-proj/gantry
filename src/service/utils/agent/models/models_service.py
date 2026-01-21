"""Model Management Service."""

from src.db.session import AsyncSessionManager

from .settings import ModelsSettings
from .model_config import ModelConfig, ModelProvider

from structlog.stdlib import BoundLogger
from pydantic_ai.models import Model
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.anthropic import AnthropicProvider


class ModelsService:
    """Service to manage and provide models based on configurations."""

    model_configs: dict[str, ModelConfig]

    def __init__(
        self,
        models_settings: ModelsSettings,
        session_manager: AsyncSessionManager,
        logger: BoundLogger,
    ):
        self.model_configs = {}
        self.models_settings = models_settings
        self.session_manager = session_manager
        self.logger = logger

    def get_model(self, name: str) -> tuple[Model, ModelConfig]:
        """Retrieves a model by name."""
        config = self.model_configs.get(name)
        if not config:
            raise KeyError(f"Model {name} not found")
        match config.model_provider:
            case ModelProvider.OPENAI:
                if not self.models_settings.openai_api_key:
                    raise ValueError("OpenAI API key is not configured")
                return (
                    OpenAIChatModel(
                        model_name=config.model_name,
                        settings=config.model_settings,
                        provider=OpenAIProvider(
                            api_key=self.models_settings.openai_api_key
                        ),
                    ),
                    config,
                )
            case ModelProvider.ANTHROPIC:
                if not self.models_settings.anthropic_api_key:
                    raise ValueError("Anthropic API key is not configured")
                return (
                    AnthropicModel(
                        model_name=config.model_name,
                        settings=config.model_settings,
                        provider=AnthropicProvider(
                            api_key=self.models_settings.anthropic_api_key
                        ),
                    ),
                    config,
                )
            case ModelProvider.GROQ:
                if not self.models_settings.groq_api_key:
                    raise ValueError("Groq API key is not configured")
                return (
                    GroqModel(
                        model_name=config.model_name,
                        settings=config.model_settings,
                        provider=GroqProvider(
                            api_key=self.models_settings.groq_api_key
                        ),
                    ),
                    config,
                )
            case _:
                raise ValueError(
                    f"Unsupported model provider: {config.model_provider}"
                )

    def set_model_config(self, name: str, config: ModelConfig):
        """Sets or updates a model configuration."""
        self.model_configs[name] = config

    async def load_model_config(self):
        """Loads model configurations from db."""
        # TODO: Load from DB
        self.logger.debug(
            "Loading model config from database"
        )
        self.set_model_config(
            "GROQ_SMALL_MODEL",
            ModelConfig(
                model_provider=ModelProvider.GROQ,
                model_name="openai/gpt-oss-20b",
                model_settings={
                    "max_tokens": 32000,
                    "parallel_tool_calls": True,
                    "extra_body": {
                        "reasoning_effort": "low",
                    },
                },
            ),
        )
