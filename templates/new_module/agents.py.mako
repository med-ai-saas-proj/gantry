"""This file contain definition of ${app_name}'s llm agents."""

from gantry.shared import llms

from pydantic_ai import Agent
from pydantic_ai.models import Model
from gantry.shared.agents.shared_instruction import add_current_date


def create_agent(llm: Model):
    return Agent(
        model=llm,
        instructions=[add_current_date],
    )
