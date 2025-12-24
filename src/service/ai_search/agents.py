from src.shared import llms
from src.shared.agents.tools.web import WEB_TOOLSET_NAME, ViewedUrlsMixin
from src.shared.agents.agent_manager import AgentConstructorContext
from src.shared.agents.shared_instruction import add_current_date
from src.shared.agents.agent_manager_factories import getAgentManager

from pydantic_ai import Agent


class Dep(ViewedUrlsMixin):
    pass


AI_SEARCH_AGENT_NAME = "ai_search_agent"
AI_SEARCH_AGENT_PROMPT_ID = "ai_search_agent_prompt"

agent_manager = getAgentManager()


def ai_search_agent_constructor(ctx: AgentConstructorContext):
    """Constructs the AI Search Agent."""
    prompt = ctx.use_prompt(AI_SEARCH_AGENT_PROMPT_ID)
    web_toolset = ctx.use_toolset(WEB_TOOLSET_NAME)

    return Agent(
        model=llms.big_model,
        # output_type=AnswerStruct,
        # deps_type=Dep,
        name=AI_SEARCH_AGENT_NAME,
        end_strategy="exhaustive",
        toolsets=[web_toolset],
        instructions=[
            add_current_date,
            prompt,
        ],
    )
