import enum
from dataclasses import dataclass

from pydantic_ai import ModelSettings


class ModelProvider(enum.Enum):
    """Enumeration of supported model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


@dataclass
class ModelConfig:
    """Model configuration definition."""

    model_name: str
    model_provider: ModelProvider
    model_settings: ModelSettings
