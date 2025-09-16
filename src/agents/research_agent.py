from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from .shared_instruction import add_current_date

from src.consts.env import EnvConsts

research_planning_model = AnthropicModel(
    "claude-4-opus-20250514",
    provider=AnthropicProvider(api_key=EnvConsts.ANTHROPIC_API_KEY),
    settings={"max_tokens": 32000},
)

worker_model = AnthropicModel(
    "claude-4-sonnet-20250514",
    provider=AnthropicProvider(api_key=EnvConsts.ANTHROPIC_API_KEY),
    settings={"max_tokens": 32000},
)

report_model = AnthropicModel(
    "claude-4-opus-20250514",
    provider=AnthropicProvider(api_key=EnvConsts.ANTHROPIC_API_KEY),
    settings={"max_tokens": 64000},
)
