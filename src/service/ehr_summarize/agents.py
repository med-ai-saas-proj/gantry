"""EHR Summarize Agent construction and dependencies."""

from .consts import EHR_SUMMARIZE_AGENT_ID
from ..utils.agent.factories import getPromptService
from ..utils.agent.agent_deps import AgentDeps
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.shared_instruction import add_current_date
from ..utils.agent.models.model_config import ModelConfig

from functools import lru_cache

from pydantic_ai import Agent


prompt_service = getPromptService()


@lru_cache(1)
def getEhrSummarizeAgent() -> Agent[AgentDeps, str]:
    """Construct EHR Summarize Agent."""
    return Agent[AgentDeps, str](
        end_strategy="exhaustive",
        name=EHR_SUMMARIZE_AGENT_ID,
        instructions=[
            add_current_date,
            prompt_service.get_agent_instruction,
        ],
        deps_type=AgentDeps,
    )


def constructEhrSummarizeAgentDeps(
    api_key_info: ApiKeyInfo, model_config: ModelConfig
) -> AgentDeps:
    """Construct EHR Summarize Agent dependencies."""
    return AgentDeps(
        agent_id=EHR_SUMMARIZE_AGENT_ID,
        api_key_info=api_key_info,
        model_config=model_config,
    )
