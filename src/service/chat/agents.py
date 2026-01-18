"""This file contain definition of chat's llm agents."""
from src.service.chat.consts import CHAT_AGENT_ID
from src.service.utils.agent.factories import getModelService, getPromptService
from src.service.utils.agent.agent_deps import AgentDeps

from ..utils.agent.shared_instruction import add_current_date

from functools import lru_cache

from pydantic_ai import Agent


@lru_cache(1)
def getChatAgent(llm_id: str) -> Agent[AgentDeps, str]:
    print("Creating chat agent with LLM ID:", llm_id)
    model_service = getModelService()
    prompt_service = getPromptService()
    print(model_service)
    return Agent[AgentDeps, str](
        name=CHAT_AGENT_ID,
        model=model_service.get_model(llm_id),
        instructions=[
            add_current_date,
            prompt_service.get_agent_instruction,
        ],
        deps_type=AgentDeps,
    )


def constructChatAgentDeps(
    api_key_info,
) -> AgentDeps:
    return AgentDeps(
        agent_id=CHAT_AGENT_ID,
        api_key_info=api_key_info,
    )
