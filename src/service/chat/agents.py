"""This file contain definition of chat's llm agents."""

from src.shared import llms
from src.shared.agents.shared_instruction import add_current_date

from pydantic_ai import Agent
from pydantic_ai.models import Model


def create_agent(llm: Model):
    return Agent(
        model=llm,
        instructions=[add_current_date, "You are a friendly chatbot"],
    )
