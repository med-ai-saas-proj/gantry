from functools import lru_cache

from src.service.ai_search.consts import AI_SEARCH_AGENT_ID
from src.service.utils.agent.agent_deps import AgentDeps

from ..utils.agent.factories import getModelService, getPromptService
from ..utils.agent.tools.web import WEB_TOOLSET
from ..utils.agent.shared_instruction import add_current_date

from pydantic_ai import Agent


model_service = getModelService()
prompt_service = getPromptService()

@lru_cache(1)
def getAiSearchAgent(llm_id: str) -> Agent[AgentDeps, str]:
    return Agent[AgentDeps, str](
        model=model_service.get_model(llm_id),
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
    api_key_info,
) -> AgentDeps:
    return AgentDeps(
        agent_id=AI_SEARCH_AGENT_ID,
        api_key_info=api_key_info,
    )
