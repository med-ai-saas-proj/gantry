from .consts import RX_ADVISOR_AGENT_ID
from ..utils.agent.factories import getModelService, getPromptService
from ..utils.agent.tools.web import WEB_TOOLSET
from ..utils.agent.agent_deps import AgentDeps
from ..utils.agent.tools.open_fda import OPEN_FDA_TOOLSET
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.shared_instruction import add_current_date

from functools import lru_cache

from pydantic_ai import Agent


prompt_service = getPromptService()
model_service = getModelService()


@lru_cache(1)
def getRxAdvisorAgent(llm_id: str) -> Agent[AgentDeps, str]:
    return Agent[AgentDeps, str](
        model=model_service.get_model(llm_id),
        # output_type=AnswerStruct,
        name=RX_ADVISOR_AGENT_ID,
        end_strategy="exhaustive",
        toolsets=[OPEN_FDA_TOOLSET, WEB_TOOLSET],
        instructions=[
            add_current_date,
            prompt_service.get_agent_instruction,
        ],
        deps_type=AgentDeps,
    )


def constructRxAdvisorAgentDeps(
    api_key_info: ApiKeyInfo,
) -> AgentDeps:
    return AgentDeps(
        agent_id=RX_ADVISOR_AGENT_ID,
        api_key_info=api_key_info,
    )
