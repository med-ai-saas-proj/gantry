"""Chat Agent construction and dependencies."""

from .consts import CHAT_AGENT_ID
from ..utils.agent.factories import getPromptService
from ..utils.agent.agent_deps import AgentDeps
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.shared_instruction import add_current_date
from ..utils.agent.models.model_config import ModelConfig

from functools import lru_cache

from pydantic_ai import Agent


prompt_service = getPromptService()


@lru_cache(1)
def getChatAgent() -> Agent[AgentDeps, str]:
    """Construct Chat Agent."""
    return Agent[AgentDeps, str](
        name=CHAT_AGENT_ID,
        instructions=[
            add_current_date,
            prompt_service.get_agent_instruction,
        ],
        deps_type=AgentDeps,
    )


def constructChatAgentDeps(
    api_key_info: ApiKeyInfo,
    model_config: ModelConfig,
) -> AgentDeps:
    """Construct Chat Agent dependencies."""
    return AgentDeps(
        agent_id=CHAT_AGENT_ID,
        api_key_info=api_key_info,
        model_config=model_config,
    )
