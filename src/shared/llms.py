from .consts import env_const

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider


big_model = AnthropicModel(
    "claude-4-opus-20250514",
    provider=AnthropicProvider(api_key=env_const.ANTHROPIC_API_KEY),
    settings={"max_tokens": 32000, "parallel_tool_calls": True},
)

small_model = AnthropicModel(
    "claude-4-sonnet-20250514",
    provider=AnthropicProvider(api_key=env_const.ANTHROPIC_API_KEY),
    settings={"max_tokens": 32000, "parallel_tool_calls": True},
)
