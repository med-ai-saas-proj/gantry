from .consts import EHR_SUMMARIZE_AGENT_ID
from ..utils.agent.factories import getModelService, getPromptService
from ..utils.agent.agent_deps import AgentDeps
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.shared_instruction import add_current_date

from pydantic_ai import Agent


prompt_service = getPromptService()
model_service = getModelService()


def getEhrSummarizeAgent(llm_id: str) -> Agent[AgentDeps, str]:
    return Agent[AgentDeps, str](
        model=model_service.get_model(llm_id),
        end_strategy="exhaustive",
        name=EHR_SUMMARIZE_AGENT_ID,
        instructions=[
            add_current_date,
            prompt_service.get_agent_instruction,
        ],
        deps_type=AgentDeps,
    )


def constructEhrSummarizeAgentDeps(
    api_key_info: ApiKeyInfo,
) -> AgentDeps:
    return AgentDeps(
        agent_id=EHR_SUMMARIZE_AGENT_ID,
        api_key_info=api_key_info,
    )
