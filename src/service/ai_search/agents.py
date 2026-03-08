"""AI Search Agent construction and dependencies."""

from .consts import AI_SEARCH_AGENT_ID
from ..utils.agent.factories import getPromptService
from ..utils.agent.tools.web import WEB_TOOLSET
from ..utils.agent.agent_deps import AgentDeps
from ..utils.models.model_config import ModelConfig
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.shared_instruction import add_current_date

from functools import lru_cache

from pydantic_ai import Agent


prompt_service = getPromptService()


@lru_cache(1)
def getAiSearchAgent() -> Agent[AgentDeps, str]:
    """Construct AI Search Agent."""
    return Agent[AgentDeps, str](
        # output_type=AnswerStruct,
        deps_type=AgentDeps,
        name=AI_SEARCH_AGENT_ID,
        end_strategy="exhaustive",
        toolsets=[WEB_TOOLSET],
        instructions=[
            add_current_date,
            prompt_service.get_agent_instruction,
        ],
    )


def constructAiSearchAgentDeps(
    api_key_info: ApiKeyInfo,
    model_config: ModelConfig,
) -> AgentDeps:
    """Construct AI Search Agent dependencies."""
    return AgentDeps(
        agent_id=AI_SEARCH_AGENT_ID,
        api_key_info=api_key_info,
        model_config=model_config,
    )
