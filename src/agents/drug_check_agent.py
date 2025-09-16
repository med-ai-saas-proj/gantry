from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from .shared_instruction import add_current_date
from .tools.open_fda import (
    get_drug_safety_and_interaction_info,
    get_drug_prescription_info,
    get_population_specific_drug_info,
)

from src.consts.env import EnvConsts


drug_check_agent = Agent(
    model=AnthropicModel(
        "claude-4-opus-20250514",
        provider=AnthropicProvider(api_key=EnvConsts.ANTHROPIC_API_KEY),
        settings={"max_tokens": 32000},
    ),
    instructions=[
        """
""",
        add_current_date,
    ],
    tools=[
        get_drug_prescription_info,
        get_drug_safety_and_interaction_info,
        get_population_specific_drug_info,
    ],
)
