"""This file contain definition of chat's llm agents."""

from src.shared import llms
from src.shared.agents.factories import getAgentManager
from src.shared.agents.agent_manager import AgentConstructorContext
from src.shared.agents.shared_instruction import add_current_date

from pydantic_ai import Agent


CHAT_AGENT_NAME = "chat_agent"
CHAT_AGENT_PROMPT_ID = "chat_agent_prompt"

agent_manager = getAgentManager()
agent_manager.register_prompt(
    CHAT_AGENT_PROMPT_ID,
    "You are a friendly chatbot"
)

def chat_agent_constructor(ctx: AgentConstructorContext):
    """Construct chat agent."""
    prompt = ctx.use_prompt(CHAT_AGENT_PROMPT_ID)
    return Agent(
        name=CHAT_AGENT_NAME,
        model=llms.small_model,
        instructions=[add_current_date, prompt],
    )

agent_manager.register_agent(
    CHAT_AGENT_NAME,
    chat_agent_constructor,
)