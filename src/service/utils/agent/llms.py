import os

from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from src.service.utils.agent.factories import getModelService
from src.service.utils.agent.model_service import ModelService

GROQ_API_KEY = os.environ["GROQ_API_KEY"]

GROQ_BIG_MODEL = "openai/gpt-oss-20b"
GROQ_MEDIUM_MODEL = "openai/gpt-oss-20b"
GROQ_SMALL_MODEL = "openai/gpt-oss-20b"

groq_big_model = GroqModel(
    GROQ_BIG_MODEL,
    provider=GroqProvider(api_key=GROQ_API_KEY),
    settings={
        "max_tokens": 32000,
        "parallel_tool_calls": True,
        "extra_body": {
            "reasoning_effort": "low",
        },
    },
)

groq_medium_model = GroqModel(
    GROQ_MEDIUM_MODEL,
    provider=GroqProvider(api_key=GROQ_API_KEY),
    settings={
        "max_tokens": 32000,
        "parallel_tool_calls": True,
        "extra_body": {
            "reasoning_effort": "low",
        },
    },
)

groq_small_model = GroqModel(
    GROQ_SMALL_MODEL,
    provider=GroqProvider(api_key=GROQ_API_KEY),
    settings={
        "max_tokens": 32000,
        "parallel_tool_calls": True,
        "extra_body": {
            "reasoning_effort": "low",
        },
    },
)

model_service = getModelService()
model_service.add_model(GROQ_BIG_MODEL, groq_big_model)

model_service.add_model(GROQ_MEDIUM_MODEL, groq_medium_model)

model_service.add_model(GROQ_SMALL_MODEL, groq_small_model)

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
