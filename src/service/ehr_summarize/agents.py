"""Setup the EHR Summary Agent."""

from src.shared import llms
from src.shared.agents.agent_manager import AgentConstructorContext
from src.shared.agents.shared_instruction import add_current_date
from src.shared.agents.agent_manager_factories import getAgentManager

from pydantic_ai import Agent


agent_manager = getAgentManager()

EHR_SUMMARY_AGENT_NAME = "ehr_summary_agent"
EHR_SUMMARY_AGENT_PROMPT_ID = "ehr_summary_agent_prompt"

def ehr_summary_agent_constructor(ctx: AgentConstructorContext) -> Agent:
    """Constructs an EHR Summary Agent."""
    prompt = ctx.use_prompt(EHR_SUMMARY_AGENT_PROMPT_ID)

    return Agent(
        model=llms.big_model,
        end_strategy="exhaustive",
        name=EHR_SUMMARY_AGENT_NAME,
        instructions=[
            add_current_date,
            prompt,
        ],
    )


agent_manager.register_agent(
    EHR_SUMMARY_AGENT_NAME, ehr_summary_agent_constructor
)
