from .consts import env_const

from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider


big_model = GroqModel(
    "openai/gpt-oss-20b",
    provider=GroqProvider(api_key=env_const.GROQ_API_KEY),
    settings={
        "max_tokens": 32000,
        "parallel_tool_calls": True,
        "extra_body": {
            "reasoning_effort": "low",
        },
    },
)

medium_model = GroqModel(
    "openai/gpt-oss-20b",
    provider=GroqProvider(api_key=env_const.GROQ_API_KEY),
    settings={
        "max_tokens": 32000,
        "parallel_tool_calls": True,
        "extra_body": {
            "reasoning_effort": "low",
        },
    },
)

small_model = GroqModel(
    "openai/gpt-oss-20b",
    provider=GroqProvider(api_key=env_const.GROQ_API_KEY),
    settings={
        "max_tokens": 32000,
        "parallel_tool_calls": True,
        "extra_body": {
            "reasoning_effort": "low",
        },
    },
)


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
