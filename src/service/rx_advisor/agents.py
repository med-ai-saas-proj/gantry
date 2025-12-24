"""Sets up the Rx-Advisor agent."""

from src.shared import llms
from src.shared.agents.tools.web import WEB_TOOLSET_NAME
from src.shared.agents.shared_types import AnswerStruct
from src.shared.agents.agent_manager import AgentConstructorContext
from src.shared.agents.tools.open_fda import OPEN_FDA_TOOLSET_NAME
from src.shared.agents.shared_instruction import add_current_date
from src.shared.agents.agent_manager_factories import getAgentManager

from pydantic_ai import Agent


RX_ADVISOR_AGENT_NAME = "rx_advisor_agent"
RX_ADVISOR_AGENT_PROMPT_ID = "rx_advisor_agent_prompt"

agent_manager = getAgentManager()


def rxAdvisorAgentConstructor(ctx: AgentConstructorContext):
    """Constructs the Rx-Advisor agent with specified prompt and tools."""
    prompt = ctx.use_prompt(RX_ADVISOR_AGENT_PROMPT_ID)

    open_fda_toolset = ctx.use_toolset(OPEN_FDA_TOOLSET_NAME)
    web_toolset = ctx.use_toolset(WEB_TOOLSET_NAME)

    return Agent(
        model=llms.small_model,
        output_type=AnswerStruct,
        name=RX_ADVISOR_AGENT_NAME,
        end_strategy="exhaustive",
        toolsets=[
            open_fda_toolset,
            web_toolset,
        ],
        instructions=[
            add_current_date,
            prompt,
        ],
    )


agent_manager.register_agent(
    RX_ADVISOR_AGENT_NAME,
    rxAdvisorAgentConstructor,
)
